import streamlit as st
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
import db
import logger

_user = st.session_state.get("user_name", "?")
logger.debug(_user, "results.py: page load")

# Check if game was reset by admin (state flipped back to WAITING)
if not db.check_game_started():
    logger.warning(_user, "results.py: game_started=False detected -> resetting session and returning to app.py")
    st.session_state.in_lobby = False
    st.session_state.was_in_lobby_before_start = False
    st.switch_page("app.py")

# Admin should never land here
if st.session_state.get("is_admin", False):
    st.switch_page("pages/admin.py")
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

# Guard: if core quiz state is missing, this is a stale/direct-navigation session
if 'correct_count' not in st.session_state or 'questions' not in st.session_state:
    logger.warning(_user, "results.py: correct_count or questions missing from session state — redirecting to app.py")
    st.switch_page("app.py")

# Save current player's score (only once)
if 'score_saved' not in st.session_state:
    logger.info(_user, f"results.py: saving score {st.session_state.correct_count}/{len(st.session_state.questions)}")
    db.save_player_score(st.session_state.user_name, st.session_state.correct_count, len(st.session_state.questions))
    st.session_state.score_saved = True

# Show balloons
if 'balloons_shown_results' not in st.session_state:
    st.balloons()
    st.session_state.balloons_shown_results = True

# Create a clean, centered final score page
st.markdown("<br><br>", unsafe_allow_html=True)

col1, col2, col3 = st.columns([1, 2, 1])
with col2:
    st.markdown(f"<h1 style='text-align: center;'>🎉 Quiz Complete! 🎉</h1>", unsafe_allow_html=True)
    st.markdown(f"<h2 style='text-align: center;'>Well done, {st.session_state.user_name}!</h2>", unsafe_allow_html=True)
    st.markdown(f"<h2 style='text-align: center;'>Your Score</h2>", unsafe_allow_html=True)
    st.markdown(f"<h1 style='text-align: center; color: #28a745;'>{st.session_state.correct_count}/{len(st.session_state.questions)}</h1>", unsafe_allow_html=True)
    
    percentage = (st.session_state.correct_count / len(st.session_state.questions)) * 100
    st.markdown(f"<h3 style='text-align: center;'>{percentage:.1f}%</h3>", unsafe_allow_html=True)
    
    st.markdown("<br>", unsafe_allow_html=True)

    # ── Leaderboard — refreshes every 3 s as other players finish ────────────
    # Using @st.fragment so only this section reruns, not the whole page.
    # This eliminates the "ghost" double-render caused by full-page st.rerun().
    @st.fragment(run_every=3)
    def _leaderboard():
        st.markdown("<h2 style='text-align: center;'>🏆 Leaderboard 🏆</h2>", unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)

        all_scores = db.read_all_scores()

        for i, player_score in enumerate(all_scores, 1):
            medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
            highlight = "background-color: #d4edda; padding: 10px; border-radius: 5px;" if player_score["name"] == st.session_state.user_name else "padding: 10px;"
            st.markdown(f"<div style='{highlight}'><p style='text-align: center; font-size: 18px;'>{medal} {player_score['name']}: {player_score['score']}/{player_score['total']} ({player_score['percentage']:.1f}%)</p></div>", unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("<p style='text-align: center; color: gray; font-size: 14px;'>Leaderboard updates as other players finish...</p>", unsafe_allow_html=True)

    _leaderboard()

    st.markdown("<br>", unsafe_allow_html=True)
    
    if st.button("Back to Login", use_container_width=True, type="primary"):
        logger.info(_user, "results.py: Back to Login clicked -> clearing session state only (admin resets game)")
        # Reset only this player's session state — do NOT call reset_everything().
        # The admin's 'End Game & Reset' button is the authoritative reset so that
        # one player finishing early cannot wipe the game for everyone else.
        st.session_state.current_question = 0
        st.session_state.selected_answer = None
        st.session_state.show_result = False
        st.session_state.result_start_time = None
        st.session_state.timer_start = None
        st.session_state.correct_count = 0
        st.session_state.countdown_start_time = None
        st.session_state.in_lobby = False
        st.session_state.score_saved = False
        st.session_state.balloons_shown_results = False
        if "was_in_lobby_before_start" in st.session_state:
            del st.session_state.was_in_lobby_before_start
        st.switch_page("app.py")
