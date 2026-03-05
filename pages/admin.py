import streamlit as st
import json
import time
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
import db

# ── Guard ──────────────────────────────────────────────────────────────────────
# Only actual admins may see this page
if not st.session_state.get("is_admin", False):
    st.switch_page("app.py")

# ── CSS ────────────────────────────────────────────────────────────────────────
st.markdown("""
    <style>
    .stButton > button[kind="primary"] {
        background-color: #28a745;
        border-color: #28a745;
    }
    .stButton > button[kind="primary"]:hover {
        background-color: #218838;
        border-color: #1e7e34;
    }
    </style>
""", unsafe_allow_html=True)

# ── Helpers (thin wrappers — real work done in db.py) ────────────────────────
read_lobby_players = db.read_lobby_players
check_game_started = db.check_game_started
start_game         = db.start_game
reset_everything   = db.reset_everything

# ── Layout ─────────────────────────────────────────────────────────────────────
st.markdown("<br>", unsafe_allow_html=True)

col1, col2, col3 = st.columns([1, 2, 1])
with col2:
    st.markdown("<h1 style='text-align: center;'>🛠️ Admin Room 🛠️</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: gray;'>You are logged in as <strong>admin</strong>. "
                "You are not visible to players.</p>", unsafe_allow_html=True)
    st.markdown("<hr>", unsafe_allow_html=True)

    # ── Game status ──────────────────────────────────────────────────────────
    game_started = check_game_started()
    if game_started:
        st.markdown("<h4 style='text-align: center; color: #e67e22;'>⚡ Game is currently IN PROGRESS</h4>",
                    unsafe_allow_html=True)
    else:
        st.markdown("<h4 style='text-align: center; color: #28a745;'>⏳ Game is WAITING to start</h4>",
                    unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Lobby player list ─────────────────────────────────────────────────────
    players = read_lobby_players()
    st.markdown(f"<h4 style='text-align: center;'>Players in Lobby: {len(players)}</h4>",
                unsafe_allow_html=True)
    if players:
        for i, player in enumerate(players, 1):
            st.markdown(f"<p style='text-align: center; font-size: 16px;'>{i}. {player}</p>",
                        unsafe_allow_html=True)
    else:
        st.markdown("<p style='text-align: center; color: gray;'>No players yet.</p>",
                    unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("<hr>", unsafe_allow_html=True)

    # ── Start Quiz ────────────────────────────────────────────────────────────
    st.markdown("<h4>🚀 Start Quiz</h4>", unsafe_allow_html=True)
    st.markdown("<p style='color: gray; font-size: 14px;'>Sends all players in the lobby into the countdown.</p>",
                unsafe_allow_html=True)
    if st.button("▶ Start Quiz for Everyone", use_container_width=True, type="primary",
                 disabled=game_started, key="btn_start"):
        start_game()
        st.success("Quiz started! Players will be redirected automatically.")
        st.rerun()

    st.markdown("<br>", unsafe_allow_html=True)

    # ── End / Reset ───────────────────────────────────────────────────────────
    st.markdown("<h4>🔴 End Game &amp; Reset</h4>", unsafe_allow_html=True)
    st.markdown("<p style='color: gray; font-size: 14px;'>Clears all lobby, score and game-state files. "
                "Players will be returned to the home screen.</p>", unsafe_allow_html=True)
    if st.button("🔴 End Game & Reset Everything", use_container_width=True, type="secondary",
                 key="btn_reset"):
        reset_everything()
        # Also reset quiz data cache so a freshly-uploaded quiz is used next round
        if "questions" in st.session_state:
            del st.session_state["questions"]
        st.success("Game ended and everything has been reset.")
        st.rerun()

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("<hr>", unsafe_allow_html=True)

    # ── Upload Quiz ───────────────────────────────────────────────────────────
    st.markdown("<h4>📂 Upload Quiz File</h4>", unsafe_allow_html=True)
    st.markdown("<p style='color: gray; font-size: 14px;'>Upload a <code>.json</code> file produced by the "
                "Quiz Creator app. It will replace the active quiz immediately.</p>", unsafe_allow_html=True)

    uploaded = st.file_uploader("Choose a quiz JSON file", type=["json"], key="quiz_upload")
    if uploaded is not None:
        try:
            raw = uploaded.read()
            data = json.loads(raw)
            # Basic validation
            if "questions" not in data or "display_time" not in data:
                st.error("Invalid quiz file — must contain 'questions' and 'display_time'.")
            else:
                ok = db.save_quiz_data(data)
                if ok:
                    # Invalidate cached quiz so it reloads next round
                    for key in ["questions", "display_time", "wait_before_next"]:
                        if key in st.session_state:
                            del st.session_state[key]
                    st.success(f"✅ Quiz uploaded successfully! "
                               f"{len(data['questions'])} question(s) loaded.")
                else:
                    st.error("Upload failed — could not save to database.")
        except json.JSONDecodeError:
            st.error("Could not parse the file as JSON. Please check the file and try again.")

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("<hr>", unsafe_allow_html=True)

    # ── Play as Player ─────────────────────────────────────────────────────────
    st.markdown("<h4>🎮 Switch to Player Mode</h4>", unsafe_allow_html=True)
    st.markdown("<p style='color: gray; font-size: 14px;'>Go back to the name-entry screen and join as a "
                "regular player.</p>", unsafe_allow_html=True)
    if st.button("🎮 Play as a Regular Player", use_container_width=True, key="btn_play_as_player"):
        st.session_state.is_admin = False
        st.session_state.user_name = ""
        st.session_state.in_lobby = False
        if "was_in_lobby_before_start" in st.session_state:
            del st.session_state["was_in_lobby_before_start"]
        st.switch_page("app.py")

    st.markdown("<br>", unsafe_allow_html=True)

# Auto-refresh every 3 s so the player list and game state stay current
time.sleep(3)
st.rerun()
