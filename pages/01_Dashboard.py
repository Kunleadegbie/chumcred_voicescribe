import streamlit as st
import pandas as pd

from utils.auth import require_login, logout_user
from utils.supabase_client import get_authenticated_client
from utils.subscription import get_or_create_subscription, calculate_remaining_minutes


st.set_page_config(
    page_title="Dashboard - VoiceScribe AI",
    page_icon="📊",
    layout="wide"
)

require_login()

st.title("📊 VoiceScribe AI Dashboard")

profile = st.session_state.get("profile")
user_id = profile.get("id") if profile else None

if not user_id:
    st.error("User profile not found. Please logout and login again.")
    st.stop()

with st.sidebar:
    st.write("VoiceScribe AI")
    if st.button("Logout"):
        logout_user()

supabase = get_authenticated_client()

subscription = get_or_create_subscription(user_id)

try:
    recordings_response = (
        supabase.table("voice_recordings")
        .select("*")
        .eq("user_id", user_id)
        .execute()
    )

    transcripts_response = (
        supabase.table("voice_transcripts")
        .select("*")
        .eq("user_id", user_id)
        .execute()
    )

    recordings = recordings_response.data or []
    transcripts = transcripts_response.data or []

except Exception as e:
    st.error(f"Unable to load dashboard data: {e}")
    st.stop()


total_recordings = len(recordings)
total_transcripts = len(transcripts)
total_seconds = sum(float(r.get("duration_seconds") or 0) for r in recordings)
total_minutes_recorded = round(total_seconds / 60, 2)

transcribed_recordings = [
    r for r in recordings
    if r.get("transcription_status") == "transcribed"
]

not_transcribed = total_recordings - len(transcribed_recordings)

plan_name = subscription.get("plan_name", "Free") if subscription else "Free"
allowed_minutes = float(subscription.get("transcription_minutes") or 0) if subscription else 0
used_minutes = float(subscription.get("used_minutes") or 0) if subscription else 0
remaining_minutes = calculate_remaining_minutes(subscription) if subscription else 0

usage_percent = 0
if allowed_minutes > 0:
    usage_percent = min(used_minutes / allowed_minutes, 1.0)


st.subheader("Subscription Usage")

col1, col2, col3, col4 = st.columns(4)

col1.metric("Current Plan", plan_name)
col2.metric("Allowed Minutes", f"{allowed_minutes}")
col3.metric("Used Minutes", f"{round(used_minutes, 2)}")
col4.metric("Remaining Minutes", f"{round(remaining_minutes, 2)}")

st.progress(usage_percent)

if remaining_minutes <= 5:
    st.warning("Your transcription minutes are running low.")


st.divider()

st.subheader("Recording Statistics")

c1, c2, c3, c4 = st.columns(4)

c1.metric("Total Recordings", total_recordings)
c2.metric("Transcribed", total_transcripts)
c3.metric("Not Transcribed", not_transcribed)
c4.metric("Total Audio Minutes", total_minutes_recorded)

st.divider()

st.subheader("Quick Actions")

q1, q2, q3 = st.columns(3)

with q1:
    st.page_link("pages/02_New_Recording.py", label="🎙️ New Recording", use_container_width=True)

with q2:
    st.page_link("pages/03_My_Recordings.py", label="📁 My Recordings", use_container_width=True)

with q3:
    st.page_link("pages/05_Search_Archive.py", label="🔍 Search Archive", use_container_width=True)


st.divider()

st.subheader("Recent Recordings")

if not recordings:
    st.info("No recordings yet.")
else:
    recent = sorted(recordings, key=lambda x: x.get("created_at", ""), reverse=True)[:5]

    for rec in recent:
        with st.container(border=True):
            st.write(f"**{rec.get('title', 'Untitled Recording')}**")
            st.write(f"Category: {rec.get('category', 'Other')}")
            st.write(f"Duration: {rec.get('duration_seconds', 0)} seconds")
            st.write(f"Status: `{rec.get('transcription_status', 'not_transcribed')}`")