import streamlit as st
import time
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
import db

# Custom CSS
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

# Safety guard — admin should never be in the lobby
if st.session_state.get("is_admin", False) or st.session_state.get("user_name", "").lower() == "admin":
    st.switch_page("pages/admin.py")

# Check if game has started
game_started = db.check_game_started()

# If game started but player was already in lobby before it started, let them play
if 'was_in_lobby_before_start' not in st.session_state:
    st.session_state.was_in_lobby_before_start = not game_started

if game_started and st.session_state.was_in_lobby_before_start:
    # Player was in lobby before game started - let them play
    st.switch_page("pages/countdown.py")
elif game_started and not st.session_state.was_in_lobby_before_start:
    # Player joined AFTER game started - show "game in progress" message
    st.markdown("<br><br><br>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("<h1 style='text-align: center;'>⏳ Game in Progress ⏳</h1>", unsafe_allow_html=True)
        st.markdown("<h3 style='text-align: center;'>Sorry, you cannot join a game in progress.</h3>", unsafe_allow_html=True)
        st.markdown("<p style='text-align: center; color: gray;'>Please wait for the current game to finish.</p>", unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("Leave Lobby", use_container_width=True, type="primary"):
            st.session_state.in_lobby = False
            st.session_state.was_in_lobby_before_start = False
            st.switch_page("app.py")
    
    # Auto-refresh to check if game ended
    time.sleep(2)
    st.rerun()
    st.stop()

# Lobby Page
st.markdown("<br><br>", unsafe_allow_html=True)

col1, col2, col3 = st.columns([1, 2, 1])
with col2:
    st.markdown("<h1 style='text-align: center;'>🎯 Lobby 🎯</h1>", unsafe_allow_html=True)
    st.markdown(f"<h3 style='text-align: center;'>Welcome, {st.session_state.user_name}!</h3>", unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)
    
    # Show current players
    players = db.read_lobby_players()
    st.markdown("<h4 style='text-align: center;'>Players in Lobby:</h4>", unsafe_allow_html=True)
    
    for i, player in enumerate(players, 1):
        icon = "👤 (You)" if player == st.session_state.user_name else ""
        st.markdown(f"<p style='text-align: center; font-size: 18px;'>{i}. {player} {icon}</p>", unsafe_allow_html=True)
    
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: gray; font-size: 14px;'>Waiting for the host to start the quiz... Page refreshes automatically.</p>", unsafe_allow_html=True)

# Auto-refresh every 2 seconds to check for new players or game start
time.sleep(2)
st.rerun()
