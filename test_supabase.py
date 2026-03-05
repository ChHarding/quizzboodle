"""
test_supabase.py
Run with:  python test_supabase.py

Tests every function in db.py against the live Supabase project.
All test data is cleaned up automatically at the end.
No pytest required.
"""

import sys
import os
import json
import types
import traceback

# ── 0. Read secrets WITHOUT streamlit ─────────────────────────────────────────
SECRETS_PATH = os.path.join(os.path.dirname(__file__), ".streamlit", "secrets.toml")

try:
    import tomllib                        # Python 3.11+
    with open(SECRETS_PATH, "rb") as f:
        _secrets = tomllib.load(f)
except ModuleNotFoundError:
    try:
        import tomli as tomllib           # pip install tomli  (< 3.11)
        with open(SECRETS_PATH, "rb") as f:
            _secrets = tomllib.load(f)
    except ModuleNotFoundError:
        # Manual minimal TOML parser (handles only [section] + key = "value")
        _secrets = {}
        _section = None
        with open(SECRETS_PATH, "r") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if line.startswith("["):
                    _section = line.strip("[]").strip()
                    _secrets[_section] = {}
                elif "=" in line and _section:
                    k, _, v = line.partition("=")
                    _secrets[_section][k.strip()] = v.strip().strip('"').strip("'")

SUPABASE_URL = _secrets["supabase"]["url"]
SUPABASE_KEY = _secrets["supabase"]["key"]

# ── 1. Stub out Streamlit so db.py can be imported outside a Streamlit app ─────
_fake_secrets = {"supabase": {"url": SUPABASE_URL, "key": SUPABASE_KEY}}

class _SecretsProxy(dict):
    """dict subclass that also supports attribute access."""
    def __getattr__(self, item):
        val = self[item]
        if isinstance(val, dict):
            return _SecretsProxy(val)
        return val
    def __getitem__(self, item):
        val = super().__getitem__(item)
        if isinstance(val, dict):
            return _SecretsProxy(val)
        return val

_st_stub = types.ModuleType("streamlit")
_st_stub.secrets = _SecretsProxy(_fake_secrets)
_st_stub.cache_resource = lambda func: func   # no-op decorator
sys.modules["streamlit"] = _st_stub

# ── 2. Now import db ───────────────────────────────────────────────────────────
import db  # noqa: E402  (must come after stub)

# ── 3. Test harness helpers ────────────────────────────────────────────────────
_results = []

GREEN  = "\033[92m"
RED    = "\033[91m"
YELLOW = "\033[93m"
RESET  = "\033[0m"

def run_test(name: str, fn):
    """Run fn(); record PASS / FAIL."""
    try:
        fn()
        print(f"  {GREEN}PASS{RESET}  {name}")
        _results.append((name, True, None))
    except Exception as exc:
        print(f"  {RED}FAIL{RESET}  {name}")
        print(f"         {YELLOW}{exc}{RESET}")
        _results.append((name, False, traceback.format_exc()))


def section(title: str):
    print(f"\n{'─'*55}")
    print(f" {title}")
    print(f"{'─'*55}")


# ── 4. Test suite ──────────────────────────────────────────────────────────────

section("CONNECTION")

def test_connection():
    """get_client() returns a usable Supabase client."""
    client = db.get_client()
    assert client is not None, "Client is None"
    # A simple ping — select from game_state (always has 1 row)
    result = client.table("game_state").select("id").eq("id", 1).execute()
    assert result.data, "game_state row 1 not found — did you run the setup SQL?"

run_test("Supabase client connects and game_state row exists", test_connection)


section("GAME STATE")

def test_reset_sets_waiting():
    db.reset_everything()
    assert not db.check_game_started(), "Expected WAITING after reset"

run_test("reset_everything() → game is WAITING", test_reset_sets_waiting)


def test_start_game():
    db.start_game()
    assert db.check_game_started(), "Expected STARTED after start_game()"

run_test("start_game() → game is STARTED", test_start_game)


def test_reset_after_start():
    db.reset_everything()
    assert not db.check_game_started(), "Expected WAITING after second reset"

run_test("reset_everything() after start → back to WAITING", test_reset_after_start)


section("LOBBY")

_TEST_PLAYER_1 = "__test_player_alpha__"
_TEST_PLAYER_2 = "__test_player_beta__"

def test_lobby_empty_after_reset():
    # reset_everything already called above
    players = db.read_lobby_players()
    test_players = [p for p in players if p.startswith("__test_")]
    assert len(test_players) == 0, f"Stale test players found: {test_players}"

run_test("Lobby has no stale test players after reset", test_lobby_empty_after_reset)


def test_add_player():
    db.add_player_to_lobby(_TEST_PLAYER_1)
    players = db.read_lobby_players()
    assert _TEST_PLAYER_1 in players, f"{_TEST_PLAYER_1!r} not found in lobby"

run_test("add_player_to_lobby() adds a player", test_add_player)


def test_add_duplicate_player():
    db.add_player_to_lobby(_TEST_PLAYER_1)   # add again
    players = db.read_lobby_players()
    count = players.count(_TEST_PLAYER_1)
    assert count == 1, f"Duplicate entry: {_TEST_PLAYER_1!r} appeared {count} times"

run_test("add_player_to_lobby() is idempotent (no duplicates)", test_add_duplicate_player)


def test_add_second_player():
    db.add_player_to_lobby(_TEST_PLAYER_2)
    players = db.read_lobby_players()
    assert _TEST_PLAYER_2 in players, f"{_TEST_PLAYER_2!r} not found in lobby"
    assert len([p for p in players if p.startswith("__test_")]) == 2

run_test("add_player_to_lobby() supports multiple players", test_add_second_player)


def test_reset_clears_lobby():
    db.reset_everything()
    players = db.read_lobby_players()
    assert _TEST_PLAYER_1 not in players, "Player 1 still in lobby after reset"
    assert _TEST_PLAYER_2 not in players, "Player 2 still in lobby after reset"

run_test("reset_everything() clears the lobby", test_reset_clears_lobby)


section("SCORES")

def test_save_score():
    db.save_player_score(_TEST_PLAYER_1, 7, 10)
    scores = db.read_all_scores()
    names = [s["name"] for s in scores]
    assert _TEST_PLAYER_1 in names, "Score not found after save"

run_test("save_player_score() saves a score", test_save_score)


def test_score_fields():
    db.save_player_score(_TEST_PLAYER_2, 4, 10)
    scores = db.read_all_scores()
    p1 = next((s for s in scores if s["name"] == _TEST_PLAYER_1), None)
    p2 = next((s for s in scores if s["name"] == _TEST_PLAYER_2), None)
    assert p1 is not None, "Player 1 score missing"
    assert p2 is not None, "Player 2 score missing"
    assert p1["score"] == 7 and p1["total"] == 10
    assert abs(p1["percentage"] - 70.0) < 0.01
    assert p2["score"] == 4 and p2["total"] == 10

run_test("read_all_scores() returns correct fields and values", test_score_fields)


def test_scores_sorted():
    scores = db.read_all_scores()
    test_scores = [s for s in scores if s["name"].startswith("__test_")]
    assert len(test_scores) >= 2
    assert test_scores[0]["score"] >= test_scores[1]["score"], "Scores not sorted descending"

run_test("read_all_scores() is sorted descending by score", test_scores_sorted)


def test_start_game_clears_scores():
    db.start_game()
    scores = db.read_all_scores()
    names = [s["name"] for s in scores]
    assert _TEST_PLAYER_1 not in names, "Score survived start_game()"
    assert _TEST_PLAYER_2 not in names, "Score survived start_game()"

run_test("start_game() wipes previous scores", test_start_game_clears_scores)


section("QUIZ CONFIG")

_SAMPLE_QUIZ = {
    "display_time": 20,
    "wait_before_next": 3,
    "questions": [
        {
            "question": "Test question?",
            "answers": [
                {"text": "A"}, {"text": "B"}, {"text": "C"}, {"text": "D"}
            ],
            "correct_answer_index": 0
        }
    ]
}

def test_save_quiz():
    ok = db.save_quiz_data(_SAMPLE_QUIZ)
    assert ok, "save_quiz_data() returned False"

run_test("save_quiz_data() saves without error", test_save_quiz)


def test_load_quiz_from_db():
    data = db.load_quiz_data()
    assert "questions" in data, "Loaded quiz missing 'questions'"
    assert "display_time" in data, "Loaded quiz missing 'display_time'"
    assert len(data["questions"]) == 1
    assert data["questions"][0]["question"] == "Test question?"

run_test("load_quiz_data() loads back what was saved", test_load_quiz_from_db)


section("CLEANUP")

def test_final_cleanup():
    db.reset_everything()
    assert not db.check_game_started()
    assert _TEST_PLAYER_1 not in db.read_lobby_players()
    assert _TEST_PLAYER_2 not in db.read_lobby_players()
    # Scores wiped by reset
    names = [s["name"] for s in db.read_all_scores()]
    assert _TEST_PLAYER_1 not in names
    assert _TEST_PLAYER_2 not in names

run_test("Final cleanup — all tables back to clean state", test_final_cleanup)


# ── 5. Summary ─────────────────────────────────────────────────────────────────
passed = sum(1 for _, ok, _ in _results if ok)
failed = sum(1 for _, ok, _ in _results if not ok)
total  = len(_results)

print(f"\n{'═'*55}")
print(f"  Results: {GREEN}{passed} passed{RESET}  |  {RED}{failed} failed{RESET}  |  {total} total")
print(f"{'═'*55}\n")

if failed:
    print("Failed tests:\n")
    for name, ok, tb in _results:
        if not ok:
            print(f"  {RED}✗ {name}{RESET}")
            print(f"    {YELLOW}{tb}{RESET}")
    sys.exit(1)
