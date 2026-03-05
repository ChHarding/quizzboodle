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
