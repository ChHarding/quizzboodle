"""
db.py — central Supabase data-access layer.

All pages import from here instead of touching files directly.
Secrets are read from .streamlit/secrets.toml (local) or the
Streamlit Cloud secrets panel (production).
"""

import json
import os
import time
import streamlit as st
from supabase import create_client, Client
import logger

# ── Polling cache ──────────────────────────────────────────────────────────────
# How many seconds between live Supabase calls for game state.
# Pages that rerun at 0.1 s (quiz timer) will use the cached value in between.
GAME_STATE_POLL_INTERVAL: float = 2.0   # seconds — change this to tune polling rate

_game_state_cache: dict = {"value": False, "ts": 0.0}  # module-level cache


# ── Client (cached for the lifetime of the Streamlit server process) ───────────

@st.cache_resource
def get_client() -> Client:
    url = st.secrets["supabase"]["url"]
    key = st.secrets["supabase"]["key"]
    return create_client(url, key)


# ── Lobby ──────────────────────────────────────────────────────────────────────

def read_lobby_players() -> list[str]:
    """Return names of all players currently in the lobby."""
    try:
        result = get_client().table("lobby").select("player_name").execute()
        names = [row["player_name"] for row in result.data]
        logger.debug("system", f"read_lobby_players -> {names}")
        return names
    except Exception as e:
        logger.error("system", f"read_lobby_players failed: {e}")
        return []


def add_player_to_lobby(name: str) -> None:
    """Add a player; silently ignore if already present (upsert on name)."""
    if not name or not name.strip():
        logger.warning("system", "add_player_to_lobby called with blank name — ignored")
        return
    try:
        get_client().table("lobby").upsert(
            {"player_name": name}, on_conflict="player_name"
        ).execute()
        logger.info(name, "added to lobby (upsert OK)")
    except Exception as e:
        logger.error(name, f"add_player_to_lobby failed: {e}")


def remove_player_from_lobby(name: str) -> None:
    """Remove a single player from the lobby by name."""
    if not name or not name.strip():
        return
    try:
        get_client().table("lobby").delete().eq("player_name", name).execute()
        logger.info(name, "remove_player_from_lobby: removed from lobby")
    except Exception as e:
        logger.error(name, f"remove_player_from_lobby failed: {e}")


# ── Game state ─────────────────────────────────────────────────────────────────

def check_game_started() -> bool:
    """Return True if the game_state row says STARTED.

    Results are cached for GAME_STATE_POLL_INTERVAL seconds so that pages
    running at 0.1 s rerun intervals don't hammer Supabase on every frame.
    Call _invalidate_game_state_cache() to force an immediate re-fetch.
    """
    global _game_state_cache
    now = time.time()
    if now - _game_state_cache["ts"] < GAME_STATE_POLL_INTERVAL:
        return _game_state_cache["value"]   # return cached result
    try:
        result = (
            get_client()
            .table("game_state")
            .select("state")
            .eq("id", 1)
            .execute()
        )
        if result.data:
            state = result.data[0]["state"]
            started = state == "STARTED"
            _game_state_cache = {"value": started, "ts": now}
            logger.debug("system", f"check_game_started (live) -> state={state!r} -> {started}")
            return started
    except Exception as e:
        logger.error("system", f"check_game_started failed: {e}")
    return _game_state_cache["value"]   # return stale value on error


def _invalidate_game_state_cache() -> None:
    """Force the next check_game_started() call to hit Supabase."""
    global _game_state_cache
    _game_state_cache["ts"] = 0.0


def start_game() -> None:
    """Flip game_state to STARTED and wipe any previous scores."""
    try:
        client = get_client()
        client.table("game_state").update({"state": "STARTED"}).eq("id", 1).execute()
        client.table("scores").delete().neq("id", 0).execute()
        _invalidate_game_state_cache()
        logger.info("admin", "start_game: game_state set to STARTED, scores cleared")
    except Exception as e:
        logger.error("admin", f"start_game failed: {e}")


def reset_everything() -> None:
    """Clear lobby, scores; reset game_state to WAITING."""
    try:
        client = get_client()
        client.table("lobby").delete().neq("id", 0).execute()
        client.table("scores").delete().neq("id", 0).execute()
        client.table("game_state").update({"state": "WAITING"}).eq("id", 1).execute()
        _invalidate_game_state_cache()
        logger.info("admin", "reset_everything: lobby cleared, scores cleared, game_state=WAITING")
    except Exception as e:
        logger.error("admin", f"reset_everything failed: {e}")


# ── Scores ─────────────────────────────────────────────────────────────────────

def save_player_score(name: str, score: int, total: int) -> None:
    try:
        get_client().table("scores").insert(
            {"player_name": name, "score": score, "total": total}
        ).execute()
        logger.info(name, f"save_player_score: score={score}/{total}")
    except Exception as e:
        logger.error(name, f"save_player_score failed: {e}")


def read_all_scores() -> list[dict]:
    """Return scores sorted descending by score."""
    try:
        result = get_client().table("scores").select("*").execute()
        scores = [  # noqa: E501 (block continues below)
            {
                "name": row["player_name"],
                "score": row["score"],
                "total": row["total"],
                "percentage": (row["score"] / row["total"]) * 100,
            }
            for row in result.data
        ]
        logger.debug("system", f"read_all_scores -> {len(scores)} entries")
        return sorted(scores, key=lambda x: x["score"], reverse=True)
    except Exception as e:
        logger.error("system", f"read_all_scores failed: {e}")
        return []


# ── Quiz data ──────────────────────────────────────────────────────────────────

def load_quiz_data() -> dict:
    """
    Try quiz_config table first (set via admin upload).
    Falls back to local quizz_data.json so the app still works offline/locally.
    """
    try:
        result = (
            get_client()
            .table("quiz_config")
            .select("data")
            .eq("id", 1)
            .execute()
        )
        if result.data:
            data = result.data[0]["data"]
            q_count = len(data.get("questions", []))
            logger.info("system", f"load_quiz_data: loaded from Supabase ({q_count} questions)")
            return data
    except Exception as e:
        logger.error("system", f"load_quiz_data Supabase failed, falling back to local file: {e}")

    # Local fallback
    with open("quizz_data.json", "r") as f:
        data = json.load(f)
    q_count = len(data.get("questions", []))
    logger.info("system", f"load_quiz_data: loaded from local file ({q_count} questions)")
    return data


def get_db_usage() -> dict | None:
    """
    Query the Supabase Management API for DB size and per-table row counts.

    Requires two extra keys in .streamlit/secrets.toml:
        [supabase]
        management_token = "sbp_..."   # Personal Access Token from
                                        # supabase.com/dashboard/account/tokens
        project_ref      = "abcdefghijklmnopqrst"  # 20-char ref in your project URL

    Returns a dict with keys 'db_size', 'db_size_bytes', 'tables' on success,
    or None if the credentials are missing / the call fails.
    """
    try:
        import requests
        token = st.secrets["supabase"].get("management_token")
        ref   = st.secrets["supabase"].get("project_ref")
        if not token or not ref:
            logger.debug("system", "get_db_usage: management_token or project_ref not configured")
            return None

        url     = f"https://api.supabase.com/v1/projects/{ref}/database/query"
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

        # ── DB size ───────────────────────────────────────────────────────────
        size_resp = requests.post(
            url, headers=headers,
            json={"query": "SELECT pg_size_pretty(pg_database_size(current_database())) AS db_size, "
                           "pg_database_size(current_database()) AS db_size_bytes;"},
            timeout=10,
        )
        size_resp.raise_for_status()
        size_row = size_resp.json()[0]

        # ── Per-table stats ───────────────────────────────────────────────────
        tables_resp = requests.post(
            url, headers=headers,
            json={"query": "SELECT relname AS table_name, n_live_tup AS row_count, "
                           "pg_size_pretty(pg_total_relation_size(relid)) AS total_size "
                           "FROM pg_stat_user_tables ORDER BY n_live_tup DESC;"},
            timeout=10,
        )
        tables_resp.raise_for_status()

        # ── Storage size (storage.objects) ────────────────────────────────────
        storage_resp = requests.post(
            url, headers=headers,
            json={"query": "SELECT COALESCE(SUM((metadata->>'size')::bigint), 0) AS storage_bytes "
                           "FROM storage.objects;"},
            timeout=10,
        )
        storage_bytes = 0
        if storage_resp.ok:
            try:
                storage_bytes = int(storage_resp.json()[0]["storage_bytes"])
            except Exception:
                pass

        # ── Auth users (proxy for MAU) ────────────────────────────────────────
        auth_resp = requests.post(
            url, headers=headers,
            json={"query": "SELECT COUNT(*) AS user_count FROM auth.users;"},
            timeout=10,
        )
        auth_users = 0
        if auth_resp.ok:
            try:
                auth_users = int(auth_resp.json()[0]["user_count"])
            except Exception:
                pass

        result = {
            "db_size":       size_row["db_size"],
            "db_size_bytes": int(size_row["db_size_bytes"]),
            "tables":        tables_resp.json(),
            "storage_bytes": storage_bytes,
            "auth_users":    auth_users,
        }
        logger.info("system", f"get_db_usage: db_size={result['db_size']}, "
                              f"storage={storage_bytes}B, auth_users={auth_users}, "
                              f"{len(result['tables'])} tables")
        return result
    except Exception as e:
        logger.error("system", f"get_db_usage failed: {e}")
        return None


# ── Quiz image storage ────────────────────────────────────────────────────────

QUIZ_IMAGES_BUCKET = "images"


def clear_quiz_images() -> None:
    """Delete every object currently in the quiz-images storage bucket."""
    try:
        client = get_client()
        items = client.storage.from_(QUIZ_IMAGES_BUCKET).list()
        if items:
            paths = [item["name"] for item in items if item.get("name")]
            if paths:
                client.storage.from_(QUIZ_IMAGES_BUCKET).remove(paths)
                logger.info("admin", f"clear_quiz_images: removed {len(paths)} file(s)")
        else:
            logger.info("admin", "clear_quiz_images: bucket already empty")
    except Exception as e:
        logger.error("admin", f"clear_quiz_images failed: {e}")


def upload_quiz_images(data: dict) -> dict:
    """
    Walk the quiz JSON, upload every local image file to the quiz-images
    Supabase Storage bucket, and replace the local paths with public URLs.

    Also calls clear_quiz_images() first so the previous quiz's images are
    removed before the new ones are uploaded.

    Returns a deep-copy of `data` with all image paths replaced by URLs.
    If a referenced file does not exist on disk (e.g. the path is already a
    URL or the file is missing) it is left unchanged.
    """
    import copy
    import mimetypes
    data = copy.deepcopy(data)
    clear_quiz_images()
    client = get_client()
    _cache: dict[str, str] = {}   # local_path -> public_url

    def _upload(local_path: str) -> str:
        if not local_path:
            return local_path
        # Already a URL — nothing to do
        if local_path.startswith("http://") or local_path.startswith("https://"):
            return local_path
        norm = local_path.replace("\\", "/")
        if norm in _cache:
            return _cache[norm]
        if not os.path.exists(norm):
            logger.warning("admin", f"upload_quiz_images: file not found, skipping: {norm}")
            return local_path
        mime = mimetypes.guess_type(norm)[0] or "image/png"
        dest = os.path.basename(norm)
        with open(norm, "rb") as fh:
            img_bytes = fh.read()
        client.storage.from_(QUIZ_IMAGES_BUCKET).upload(
            dest, img_bytes, {"content-type": mime, "upsert": "true"}
        )
        pub_url = client.storage.from_(QUIZ_IMAGES_BUCKET).get_public_url(dest)
        _cache[norm] = pub_url
        logger.info("admin", f"upload_quiz_images: {norm} -> {pub_url}")
        return pub_url

    for q in data.get("questions", []):
        if q.get("question_image"):
            q["question_image"] = _upload(q["question_image"])
        for ans in q.get("answers", []):
            if ans.get("image"):
                ans["image"] = _upload(ans["image"])

    logger.info("admin", f"upload_quiz_images: done, {len(_cache)} unique image(s) uploaded")
    return data


def save_quiz_data(data: dict) -> bool:
    """
    Persist quiz JSON to the quiz_config table (upsert on id=1).
    Returns True on success.
    """
    try:
        get_client().table("quiz_config").upsert(
            {"id": 1, "data": data}
        ).execute()
        logger.info("admin", f"save_quiz_data: quiz uploaded ({len(data.get('questions', []))} questions)")
        return True
    except Exception as e:
        logger.error("admin", f"save_quiz_data failed: {e}")
        return False


def get_quiz_filename() -> str:
    """Return the filename of the currently active quiz, or empty string if none."""
    try:
        result = (
            get_client()
            .table("quiz_config")
            .select("data->_quiz_filename")
            .eq("id", 1)
            .execute()
        )
        if result.data:
            return result.data[0].get("_quiz_filename") or ""
    except Exception as e:
        logger.error("system", f"get_quiz_filename failed: {e}")
    return ""
