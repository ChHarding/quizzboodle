import streamlit as st
import db
import logger

# Run once per server process — seeds Supabase with the bundled quiz if empty
@st.cache_resource
def _ensure_quiz_seeded():
    db.ensure_quiz_seeded()

_ensure_quiz_seeded()

# Custom CSS to style primary buttons as green
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
    [data-testid="stSidebarNav"] { display: none; }
    [data-testid="collapsedControl"] { display: none; }
    section[data-testid="stSidebar"] { display: none; }
    </style>
    """, unsafe_allow_html=True)

# Initialize all session state variables
if 'user_name' not in st.session_state:
    st.session_state.user_name = ""
if 'is_admin' not in st.session_state:
    st.session_state.is_admin = False
if 'in_lobby' not in st.session_state:
    st.session_state.in_lobby = False
if 'current_question' not in st.session_state:
    st.session_state.current_question = 0
if 'timer_start' not in st.session_state:
    st.session_state.timer_start = None
if 'selected_answer' not in st.session_state:
    st.session_state.selected_answer = None
if 'show_result' not in st.session_state:
    st.session_state.show_result = False
if 'result_start_time' not in st.session_state:
    st.session_state.result_start_time = None
if 'correct_count' not in st.session_state:
    st.session_state.correct_count = 0

# Load quiz data (from Supabase or local fallback) only once per session
if 'questions' not in st.session_state:
    data = db.load_quiz_data()
    st.session_state.questions = data["questions"]
    st.session_state.display_time = data["display_time"]
    st.session_state.wait_before_next = data["wait_before_next"]

# Route returning admin back to admin room
if st.session_state.is_admin:
    logger.debug("admin", "app.py: returning admin -> pages/admin.py")
    st.switch_page("pages/admin.py")

# Route returning player back to lobby
if st.session_state.in_lobby:
    user = st.session_state.user_name or "?"
    logger.debug(user, "app.py: returning player to lobby -> pages/lobby.py")
    st.switch_page("pages/lobby.py")

# Landing Page - Name Entry
st.markdown("<br><br><br>", unsafe_allow_html=True)

col1, col2, col3 = st.columns([1, 2, 1])
with col2:
    st.markdown("<h1 style='text-align: center;'>🎯 Quizzboodle 🎯</h1>", unsafe_allow_html=True)
    st.markdown("<h3 style='text-align: center;'>Multiplayer Quiz!</h3>", unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)
    
    # Name input
    name = st.text_input("Enter your name:", value=st.session_state.user_name, placeholder="Your name here...")

    st.markdown("<br>", unsafe_allow_html=True)

    # Join button — admin goes to admin room, everyone else joins the lobby
    if st.button("Join", use_container_width=True, type="primary", disabled=len(name.strip()) == 0):
        st.session_state.user_name = name.strip()
        if st.session_state.user_name.lower() == "admin":
            st.session_state.is_admin = True
            logger.info("admin", "app.py: admin joined -> switching to pages/admin.py")
            st.switch_page("pages/admin.py")
        else:
            existing = db.read_lobby_players()
            if st.session_state.user_name in existing:
                logger.warning(st.session_state.user_name, "app.py: duplicate name rejected — already in lobby")
                st.warning(f"⚠️ The name **{st.session_state.user_name}** is already taken in the lobby. Please choose a different name.")
                st.session_state.user_name = ""
            else:
                logger.info(st.session_state.user_name, "app.py: player joined, calling add_player_to_lobby")
                db.add_player_to_lobby(st.session_state.user_name)
                st.session_state.in_lobby = True
                st.rerun()
