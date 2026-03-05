"""
logger.py — centralised logging for Quizzboodle.

All pages import this module and call the helpers below.
A single log file (quizzboodle.log) is written in the project root.
Each line includes a timestamp, log level, user name, and message.

Usage:
    import logger
    logger.debug("Bob",  "entered lobby page")
    logger.info ("admin", "started the game")
    logger.warning("Alice", "was_in_lobby_before_start is False — will be blocked")
    logger.error("system", f"Supabase error in start_game: {e}")
"""

import logging
import os

# ── File location ──────────────────────────────────────────────────────────────
_LOG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "quizzboodle.log")

# ── One-time setup (safe to import from multiple modules) ──────────────────────
_logger = logging.getLogger("quizzboodle")

if not _logger.handlers:          # avoid duplicate handlers on Streamlit reruns
    _logger.setLevel(logging.DEBUG)

    # mode='w' overwrites the file each time the Streamlit server (re)starts.
    # Because of the `if not _logger.handlers` guard this only runs once per
    # server process, so individual page reruns do NOT wipe the log.
    _handler = logging.FileHandler(_LOG_FILE, mode="w", encoding="utf-8")
    _handler.setLevel(logging.DEBUG)

    _formatter = logging.Formatter(
        fmt="%(asctime)s [%(levelname)-7s] [%(user)-12s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    _handler.setFormatter(_formatter)
    _logger.addHandler(_handler)


# ── Public helpers ─────────────────────────────────────────────────────────────

def _log(level: int, user: str, message: str) -> None:
    """Internal dispatcher."""
    _logger.log(level, message, extra={"user": user or "?"})


def debug(user: str, message: str) -> None:
    """Low-level trace information (page loads, state values, routing decisions)."""
    _log(logging.DEBUG, user, message)


def info(user: str, message: str) -> None:
    """Significant events (joining, starting game, answering, saving score)."""
    _log(logging.INFO, user, message)


def warning(user: str, message: str) -> None:
    """Unexpected but recoverable situations."""
    _log(logging.WARNING, user, message)


def error(user: str, message: str) -> None:
    """Errors and caught exceptions."""
    _log(logging.ERROR, user, message)
