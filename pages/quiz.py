import streamlit as st
import json
from PIL import Image
import time
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
import db
import logger


def _load_image(src: str):
    """Return src unchanged if it is a URL (Streamlit handles it natively);
    otherwise open from disk with PIL for local dev."""
    if src.startswith("http://") or src.startswith("https://"):
        return src
    return Image.open(src)

_user = st.session_state.get("user_name", "?")

# Check if game was reset by admin (state flipped back to WAITING)
if not db.check_game_started():
    logger.warning(_user, "quiz.py: game_started=False detected -> resetting session and returning to app.py")
    st.session_state.in_lobby = False
    st.session_state.was_in_lobby_before_start = False
    st.switch_page("app.py")

# Admin should never land here
if st.session_state.get("is_admin", False):
    st.switch_page("pages/admin.py")

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
    </style>
    """, unsafe_allow_html=True)

# Start timer when question loads
if st.session_state.timer_start is None:
    st.session_state.timer_start = time.time()
    q_num = st.session_state.current_question + 1
    q_total = len(st.session_state.questions)
    logger.info(_user, f"quiz.py: question {q_num}/{q_total} timer started")

# Get current question
question_data = st.session_state.questions[st.session_state.current_question]

# Calculate remaining time
elapsed_time = time.time() - st.session_state.timer_start
remaining_time = max(0, st.session_state.display_time - elapsed_time)
progress = min(1.0, 1 - (remaining_time / st.session_state.display_time))

# Display score
st.write(f"Question {st.session_state.current_question + 1} of {len(st.session_state.questions)} | Score: {st.session_state.correct_count}/{st.session_state.current_question}")

# Display timer as progress bar (only during question time, not during result display)
if not st.session_state.show_result:
    st.progress(progress)
else:
    # Show empty progress bar during result display
    st.progress(0.0)

# Display question and its image side by side
if question_data.get("question_image"):
    col1, col2 = st.columns([1, 2])
    with col1:
        st.title("Question")
        st.subheader(question_data["question"])
    with col2:
        st.image(_load_image(question_data["question_image"]), width=300)
else:
    st.title("Question")
    st.subheader(question_data["question"])

# Display answer images in a row (if any answers have images)
answer_options = [ans["text"] for ans in question_data["answers"]]
num_answers = len(answer_options)

# Check if any answers have images
has_images = any(ans.get("image") for ans in question_data["answers"])

if has_images:
    # Create columns for answer images
    image_cols = st.columns(num_answers)
    for i, ans in enumerate(question_data["answers"]):
        with image_cols[i]:
            if ans.get("image"):
                st.image(_load_image(ans["image"]), width="stretch")

# Check if timer has expired
timer_expired = remaining_time <= 0

# If timer expired and no result shown yet, start showing result
if timer_expired and not st.session_state.show_result:
    logger.debug(_user, f"quiz.py: timer expired for Q{st.session_state.current_question + 1}, selected_answer={st.session_state.selected_answer}")
    st.session_state.show_result = True
    st.session_state.result_start_time = time.time()

# Display answer buttons in a row (only clickable during timer)
button_cols = st.columns(num_answers)
for i, ans_text in enumerate(answer_options):
    with button_cols[i]:
        # Determine button type based on selection
        button_type = "primary" if st.session_state.selected_answer == i else "secondary"
        
        if st.button(ans_text, key=f"answer_{i}", use_container_width=True, disabled=timer_expired, type=button_type):
            if not timer_expired:
                logger.info(_user, f"quiz.py: selected answer index {i} ('{ans_text}') for Q{st.session_state.current_question + 1}")
                st.session_state.selected_answer = i

# Create a placeholder for result message
result_placeholder = st.empty()

# Show result when timer expires
if st.session_state.show_result:
    correct_index = question_data["correct_answer_index"]
    
    # Check if wait time has passed since showing result
    result_elapsed = time.time() - st.session_state.result_start_time
    
    if result_elapsed < st.session_state.wait_before_next:
        # Still showing result
        with result_placeholder.container():
            if st.session_state.selected_answer is not None:
                if st.session_state.selected_answer == correct_index:
                    st.success("✅ Correct!")
                else:
                    st.error(f"❌ Incorrect! The correct answer is: {answer_options[correct_index]}")
            else:
                st.warning(f"⏰ Time's up! The correct answer is: {answer_options[correct_index]}")
        
        # Auto-refresh to check if wait time passed
        time.sleep(0.1)
        st.rerun()
    else:
        # Update score before moving to next question (only if answer was selected and correct)
        if st.session_state.selected_answer is not None and st.session_state.selected_answer == correct_index:
            st.session_state.correct_count += 1
        
        # Move to next question automatically
        if st.session_state.current_question < len(st.session_state.questions) - 1:
            # Reset all state for next question
            logger.info(_user, f"quiz.py: advancing from Q{st.session_state.current_question + 1} to Q{st.session_state.current_question + 2}")
            st.session_state.current_question += 1
            st.session_state.selected_answer = None
            st.session_state.show_result = False
            st.session_state.result_start_time = None
            st.session_state.timer_start = None  # Will be initialized on next run
            st.rerun()
        else:
            # Quiz complete - go to results page
            logger.info(_user, f"quiz.py: all questions done, score={st.session_state.correct_count}/{len(st.session_state.questions)} -> results.py")
            st.switch_page("pages/results.py")

# Auto-refresh during countdown
if not timer_expired:
    time.sleep(0.1)
    st.rerun()
