import streamlit as st
import json
import time
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
import db
import logger

# ── Guard ──────────────────────────────────────────────────────────────────────
# Only actual admins may see this page
if not st.session_state.get("is_admin", False):
    logger.warning("?", "admin.py: non-admin tried to access admin page — redirecting to app.py")
    st.switch_page("app.py")

logger.debug("admin", "admin.py: page load")

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
    [data-testid="stSidebarNav"] { display: none; }
    [data-testid="collapsedControl"] { display: none; }
    section[data-testid="stSidebar"] { display: none; }
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
    logger.debug("admin", f"admin.py: game_started={game_started}")
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
        logger.info("admin", f"admin.py: START QUIZ clicked (players in lobby: {players})")
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
        logger.info("admin", "admin.py: RESET EVERYTHING clicked")
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
    active_quiz = db.get_quiz_filename()
    if active_quiz:
        st.markdown(f"📌 **Active quiz:** `{active_quiz}`")
    else:
        st.markdown("📌 **Active quiz:** *none loaded yet*")
    uploaded = st.file_uploader("Choose a quiz JSON file", type=["json"], key="quiz_upload")
    if uploaded is not None:
        # Guard against re-processing the same file on every 3-second rerun.
        upload_id = f"{uploaded.name}_{uploaded.size}"
        if st.session_state.get("_last_upload_id") == upload_id:
            st.success(f"✅ Quiz already loaded: {uploaded.name}")
        else:
            try:
                raw = uploaded.read()
                data = json.loads(raw)
                # Basic validation
                if "questions" not in data or "display_time" not in data:
                    st.error("Invalid quiz file — must contain 'questions' and 'display_time'.")
                else:
                    # Upload any local images to Supabase Storage and rewrite paths -> URLs
                    with st.spinner("Uploading images to Supabase Storage…"):
                        data = db.upload_quiz_images(data)
                    data["_quiz_filename"] = uploaded.name
                    ok = db.save_quiz_data(data)
                    if ok:
                        st.session_state["_last_upload_id"] = upload_id
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
        logger.info("admin", "admin.py: switching to player mode")
        st.session_state.is_admin = False
        st.session_state.user_name = ""
        st.session_state.in_lobby = False
        if "was_in_lobby_before_start" in st.session_state:
            del st.session_state["was_in_lobby_before_start"]
        st.switch_page("app.py")

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("<hr>", unsafe_allow_html=True)

    # ── Supabase Usage (fragment keeps it stable during 3-s page reruns) ─────
    @st.fragment
    def _usage_panel():
        st.markdown("<h4>📊 Supabase Usage</h4>", unsafe_allow_html=True)
        with st.expander("Check database usage", expanded=False):
            if st.button("🔍 Fetch Usage Stats", key="btn_usage"):
                with st.spinner("Querying Supabase Management API..."):
                    result = db.get_db_usage()
                st.session_state["_admin_usage"] = result
                st.session_state["_admin_usage_ok"] = result is not None

            usage = st.session_state.get("_admin_usage")

            if st.session_state.get("_admin_usage_ok") is False:
                st.warning(
                    "Could not fetch usage stats. Make sure you have added "
                    "`management_token` and `project_ref` to `.streamlit/secrets.toml`:\n\n"
                    "```toml\n[supabase]\nmanagement_token = \"sbp_...\"  "
                    "# from supabase.com/dashboard/account/tokens\n"
                    "project_ref = \"abcdefghijklmnopqrst\"  "
                    "# 20-char ref in your project URL\n```"
                )
            elif usage is not None:
                def _bar(label, used, limit, unit):
                    pct = min(used / limit, 1.0)
                    colour = "🟢" if pct < 0.7 else "🟡" if pct < 0.9 else "🔴"
                    st.markdown(f"{colour} **{label}:** `{used:.1f} {unit}` of `{limit} {unit}` "
                                f"({pct*100:.1f}%)")
                    st.progress(pct)

                # ── Database size (limit: 500 MB) ────────────────────────────
                used_db_mb = usage["db_size_bytes"] / (1024 * 1024)
                _bar("Database size", used_db_mb, 500, "MB")

                # ── Storage size (limit: 1 GB) ────────────────────────────────
                used_storage_mb = usage["storage_bytes"] / (1024 * 1024)
                _bar("Storage", used_storage_mb, 1024, "MB")

                # ── Auth users (limit: 50,000 MAU) ────────────────────────────
                _bar("Auth users (total)", usage["auth_users"], 50_000, "users")

                # ── Bandwidth note (not queryable) ────────────────────────────
                st.markdown("ℹ️ **Bandwidth (egress):** limit 5 GB/month — "
                            "not available via the database API. "
                            "Check your [Supabase dashboard](https://supabase.com/dashboard) for live usage.")

                # ── Table breakdown ───────────────────────────────────────────
                st.markdown("---")
                st.markdown("**Table breakdown:**")
                for t in usage["tables"]:
                    st.markdown(
                        f"- `{t['table_name']}`: {int(t['row_count']):,} rows — {t['total_size']}"
                    )

    _usage_panel()

    st.markdown("<br>", unsafe_allow_html=True)

# Auto-refresh every 3 s so the player list and game state stay current
time.sleep(3)
st.rerun()
