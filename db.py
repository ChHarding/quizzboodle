"""
db.py — central Supabase data-access layer.

All pages import from here instead of touching files directly.
Secrets are read from .streamlit/secrets.toml (local) or the
Streamlit Cloud secrets panel (production).
"""

import json
import os
import streamlit as st
from supabase import create_client, Client


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
        return [row["player_name"] for row in result.data]
    except Exception:
        return []


def add_player_to_lobby(name: str) -> None:
    """Add a player; silently ignore if already present (upsert on name)."""
    try:
        get_client().table("lobby").upsert(
            {"player_name": name}, on_conflict="player_name"
        ).execute()
    except Exception:
        pass


# ── Game state ─────────────────────────────────────────────────────────────────

def check_game_started() -> bool:
    """Return True if the game_state row says STARTED."""
    try:
        result = (
            get_client()
            .table("game_state")
            .select("state")
            .eq("id", 1)
            .execute()
        )
        if result.data:
            return result.data[0]["state"] == "STARTED"
    except Exception:
        pass
    return False


def start_game() -> None:
    """Flip game_state to STARTED and wipe any previous scores."""
    try:
        client = get_client()
        client.table("game_state").update({"state": "STARTED"}).eq("id", 1).execute()
        client.table("scores").delete().neq("id", 0).execute()
    except Exception:
        pass


def reset_everything() -> None:
    """Clear lobby, scores; reset game_state to WAITING."""
    try:
        client = get_client()
        client.table("lobby").delete().neq("id", 0).execute()
        client.table("scores").delete().neq("id", 0).execute()
        client.table("game_state").update({"state": "WAITING"}).eq("id", 1).execute()
    except Exception:
        pass


# ── Scores ─────────────────────────────────────────────────────────────────────

def save_player_score(name: str, score: int, total: int) -> None:
    try:
        get_client().table("scores").insert(
            {"player_name": name, "score": score, "total": total}
        ).execute()
    except Exception:
        pass


def read_all_scores() -> list[dict]:
    """Return scores sorted descending by score."""
    try:
        result = get_client().table("scores").select("*").execute()
        scores = [
            {
                "name": row["player_name"],
                "score": row["score"],
                "total": row["total"],
                "percentage": (row["score"] / row["total"]) * 100,
            }
            for row in result.data
        ]
        return sorted(scores, key=lambda x: x["score"], reverse=True)
    except Exception:
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
            return result.data[0]["data"]
    except Exception:
        pass

    # Local fallback
    with open("quizz_data.json", "r") as f:
        return json.load(f)


def save_quiz_data(data: dict) -> bool:
    """
    Persist quiz JSON to the quiz_config table (upsert on id=1).
    Returns True on success.
    """
    try:
        get_client().table("quiz_config").upsert(
            {"id": 1, "data": data}
        ).execute()
        return True
    except Exception:
        return False
