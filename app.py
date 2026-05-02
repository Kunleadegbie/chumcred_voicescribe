import streamlit as st
from utils.auth import init_session, login_user, signup_user, logout_user

# =========================================================
# PAGE CONFIG (MUST BE FIRST)
# =========================================================
st.set_page_config(
    page_title="VoiceScribe AI",
    page_icon="🎙️",
    layout="wide",
    initial_sidebar_state="expanded"
)

init_session()

LOGO_PATH = "assets/chumcred_logo.png"

# =========================================================
# GLOBAL STYLES - FULL WIDTH
# =========================================================
st.markdown("""
<style>
    div[data-testid="stAppViewContainer"] {
        margin-left: 0rem !important;
        padding-left: 0rem !important;
    }

    .block-container {
        max-width: 100% !important;
        padding-top: 1.5rem !important;
        padding-left: 4rem !important;
        padding-right: 4rem !important;
        padding-bottom: 3rem !important;
    }

    header[data-testid="stHeader"] {
        background: transparent !important;
    }

    .hero {
        width: 100%;
        padding: 70px 50px;
        border-radius: 28px;
        background: linear-gradient(135deg, #0f172a 0%, #1e3a8a 55%, #2563eb 100%);
        color: white;
        margin-bottom: 35px;
    }

    .hero-title {
        font-size: 58px;
        font-weight: 900;
        line-height: 1.05;
        margin-bottom: 20px;
    }

    .hero-subtitle {
        font-size: 22px;
        color: #dbeafe;
        max-width: 850px;
        margin-bottom: 25px;
    }

    .hero-points {
        font-size: 18px;
        color: #e0f2fe;
        line-height: 1.9;
    }

    .section-title {
        font-size: 30px;
        font-weight: 800;
        margin-top: 20px;
        margin-bottom: 20px;
        color: #111827;
    }

    .card {
        background: white;
        padding: 28px;
        border-radius: 20px;
        border: 1px solid #e5e7eb;
        box-shadow: 0 8px 24px rgba(15, 23, 42, 0.08);
        min-height: 180px;
    }

    .card h4 {
        font-size: 22px;
        margin-bottom: 10px;
        color: #111827;
    }

    .card p {
        font-size: 16px;
        color: #4b5563;
    }

    .auth-box {
        background: #f8fafc;
        padding: 30px;
        border-radius: 22px;
        border: 1px solid #e5e7eb;
        box-shadow: 0 8px 24px rgba(15, 23, 42, 0.06);
    }

    .dashboard-card {
        background: #f9fafb;
        padding: 28px;
        border-radius: 20px;
        border: 1px solid #e5e7eb;
        box-shadow: 0 6px 18px rgba(15, 23, 42, 0.05);
    }

    div.stButton > button {
        border-radius: 12px;
        height: 46px;
        font-weight: 700;
    }
</style>
""", unsafe_allow_html=True)


# =========================================================
# LANDING PAGE
# =========================================================
def landing_page():
    st.image(LOGO_PATH, width=260)
    st.markdown("""
    <style>
        [data-testid="stSidebar"] {
            display: none !important;
        }

        [data-testid="stSidebarNav"] {
            display: none !important;
        }

        section[data-testid="stSidebar"] {
            display: none !important;
        }
    </style>
    """, unsafe_allow_html=True)

    left, right = st.columns([2.5, 1])

    with left:
        st.markdown("""
        <div class="hero">
            <div class="hero-title">🎙️ VoiceScribe AI</div>
            <div class="hero-subtitle">
                Record voice, transcribe to text, summarize instantly, and keep a searchable archive of your meetings, sermons, lectures, and personal notes.
            </div>
            <div class="hero-points">
                ✅ Record audio from any device &nbsp;&nbsp; | &nbsp;&nbsp;
                ✅ Convert voice to text &nbsp;&nbsp; | &nbsp;&nbsp;
                ✅ Generate summaries and action points &nbsp;&nbsp; | &nbsp;&nbsp;
                ✅ Search your archive
            </div>
        </div>
        """, unsafe_allow_html=True)

    with right:
        st.image(
            "https://cdn-icons-png.flaticon.com/512/4727/4727424.png",
            width=230
        )

    st.markdown('<div class="section-title">Core Features</div>', unsafe_allow_html=True)

    c1, c2, c3 = st.columns(3)

    with c1:
        st.markdown("""
        <div class="card">
            <h4>🎧 Smart Recording</h4>
            <p>Record meetings, church messages, lectures, interviews, training sessions, and personal notes directly from your browser.</p>
        </div>
        """, unsafe_allow_html=True)

    with c2:
        st.markdown("""
        <div class="card">
            <h4>📝 AI Transcription</h4>
            <p>Convert saved audio into clean, readable text using AI-powered speech recognition.</p>
        </div>
        """, unsafe_allow_html=True)

    with c3:
        st.markdown("""
        <div class="card">
            <h4>🔍 Searchable Archive</h4>
            <p>Find past recordings by title, category, transcript, summary, key points, or action items.</p>
        </div>
        """, unsafe_allow_html=True)

    st.divider()


# =========================================================
# AUTH PAGE
# =========================================================
def auth_page():
    st.markdown('<div class="section-title">Get Started</div>', unsafe_allow_html=True)

    left, right = st.columns([1.2, 1])

    with left:
        st.markdown("""
        <div class="auth-box">
            <h3>Built for everyday knowledge capture</h3>
            <p>
            VoiceScribe AI helps you preserve important spoken content and turn it into structured notes you can use later.
            </p>
            <p><b>Best for:</b> meetings, churches, lectures, interviews, trainings, field work, and personal reflections.</p>
        </div>
        """, unsafe_allow_html=True)

    with right:
        tab1, tab2 = st.tabs(["Login", "Create Account"])

        with tab1:
            email = st.text_input("Email", key="login_email")
            password = st.text_input("Password", type="password", key="login_password")

            if st.button("Login", use_container_width=True):
                success, msg = login_user(email, password)
                if success:
                    st.success(msg)
                    st.rerun()
                else:
                    st.error(msg)

        with tab2:
            name = st.text_input("Full Name", key="signup_name")
            email = st.text_input("Email Address", key="signup_email")
            password = st.text_input("Password", type="password", key="signup_password")
            confirm = st.text_input("Confirm Password", type="password", key="signup_confirm")

            if st.button("Create Account", use_container_width=True):
                if not name or not email or not password:
                    st.error("Please complete all required fields.")
                elif password != confirm:
                    st.error("Passwords do not match.")
                else:
                    success, msg = signup_user(email, password, name)
                    if success:
                        st.success(msg)
                    else:
                        st.error(msg)


# =========================================================
# DASHBOARD HOME
# =========================================================
def logged_in_home():
    st.image(LOGO_PATH, width=260)
    profile = st.session_state.get("profile") or {}
    name = profile.get("full_name") or "User"

    col1, col2 = st.columns([5, 1])

    with col1:
        st.markdown(f"<h1>🎙️ Welcome, {name}</h1>", unsafe_allow_html=True)
        st.caption("Your voice intelligence workspace")

    with col2:
        if st.button("Logout", use_container_width=True):
            logout_user()

    st.divider()

    st.markdown('<div class="section-title">Quick Actions</div>', unsafe_allow_html=True)

    q1, q2, q3, q4 = st.columns(4)

    with q1:
        st.page_link("pages/02_New_Recording.py", label="🎙️ New Recording")

    with q2:
        st.page_link("pages/03_My_Recordings.py", label="📁 My Recordings")

    with q3:
        st.page_link("pages/05_Search_Archive.py", label="🔍 Search Archive")

    with q4:
        st.page_link("pages/06_Subscription.py", label="💳 Subscription")

    st.divider()

    c1, c2, c3 = st.columns(3)

    with c1:
        st.markdown('<div class="dashboard-card"><h4>🎧 Record</h4><p>Create new recordings from any device.</p></div>', unsafe_allow_html=True)

    with c2:
        st.markdown('<div class="dashboard-card"><h4>📝 Transcribe</h4><p>Convert audio into readable text.</p></div>', unsafe_allow_html=True)

    with c3:
        st.markdown('<div class="dashboard-card"><h4>📊 Summarize</h4><p>Extract insights, key points, and actions.</p></div>', unsafe_allow_html=True)


# =========================================================
# ROUTING
# =========================================================
if st.session_state.logged_in:
    logged_in_home()
else:
    landing_page()
    auth_page()