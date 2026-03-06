import streamlit as st
import time
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
import db
import logger

_user = st.session_state.get("user_name", "?")
logger.debug(_user, "countdown.py: page load")

# Check if game was reset by admin (state flipped back to WAITING)
if not db.check_game_started():
    logger.warning(_user, "countdown.py: game_started=False detected -> resetting session and returning to app.py")
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
    [data-testid="stSidebarNav"] { display: none; }
    [data-testid="collapsedControl"] { display: none; }
    section[data-testid="stSidebar"] { display: none; }
    </style>
    """, unsafe_allow_html=True)

# Initialize countdown
if 'countdown_start_time' not in st.session_state or st.session_state.countdown_start_time is None:
    st.session_state.countdown_start_time = time.time()
    logger.info(_user, "countdown.py: countdown timer initialised")

countdown_elapsed = time.time() - st.session_state.countdown_start_time
countdown_remaining = max(0, 5 - countdown_elapsed)

if countdown_remaining > 0:
    st.markdown("<br><br><br><br>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown(f"<h1 style='text-align: center;'>Get Ready, {st.session_state.user_name}!</h1>", unsafe_allow_html=True)
        
        # Display countdown number
        countdown_number = int(countdown_remaining) + 1
        st.markdown(f"<h1 style='text-align: center; color: #28a745; font-size: 120px;'>{countdown_number}</h1>", unsafe_allow_html=True)
        
        # Visual progress bar for countdown
        progress = (5 - countdown_remaining) / 5
        st.progress(progress)
        
        st.markdown("<h3 style='text-align: center;'>Quiz starting soon...</h3>", unsafe_allow_html=True)
    
    # Auto-refresh during countdown
    time.sleep(0.1)
    st.rerun()
else:
    # Countdown complete, reset timer and start quiz
    logger.info(_user, "countdown.py: countdown complete -> switching to quiz.py")
    st.session_state.countdown_start_time = None
    st.switch_page("pages/quiz.py")
