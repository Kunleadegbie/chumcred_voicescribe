import streamlit as st
import pandas as pd

from utils.auth import require_login, logout_user
from utils.supabase_client import get_authenticated_client
from utils.audio_storage import create_signed_audio_url


st.set_page_config(
    page_title="My Recordings - VoiceScribe AI",
    page_icon="📁",
    layout="wide"
)

require_login()

st.title("📁 My Recordings")
st.write("Listen to saved recordings and transcribe them whenever you are ready.")

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

try:
    response = (
        supabase.table("voice_recordings")
        .select("*")
        .eq("user_id", user_id)
        .order("created_at", desc=True)
        .execute()
    )

    recordings = response.data or []

except Exception as e:
    st.error(f"Unable to load recordings: {e}")
    st.stop()


if not recordings:
    st.info("You have not saved any recording yet.")
    st.page_link("pages/02_New_Recording.py", label="🎙️ Create New Recording")
    st.stop()


search = st.text_input("Search recordings", placeholder="Search by title, category, or status...")

if search:
    search_lower = search.lower()
    recordings = [
        r for r in recordings
        if search_lower in str(r.get("title", "")).lower()
        or search_lower in str(r.get("category", "")).lower()
        or search_lower in str(r.get("transcription_status", "")).lower()
    ]


st.write(f"Total recordings: **{len(recordings)}**")

for rec in recordings:
    recording_id = rec.get("id")
    title = rec.get("title", "Untitled Recording")
    category = rec.get("category", "Other")
    duration = rec.get("duration_seconds", 0)
    transcription_status = rec.get("transcription_status", "not_transcribed")
    summary_status = rec.get("summary_status", "not_summarized")
    created_at = rec.get("created_at", "")
    audio_path = rec.get("audio_url")

    with st.container(border=True):
        col1, col2 = st.columns([3, 1])

        with col1:
            st.subheader(f"🎧 {title}")
            st.write(f"**Category:** {category}")
            st.write(f"**Duration:** {duration} seconds")
            st.write(f"**Created:** {created_at}")

        with col2:
            st.write(f"**Transcript:** `{transcription_status}`")
            st.write(f"**Summary:** `{summary_status}`")

        if audio_path:
            signed_url = create_signed_audio_url(audio_path)

            if signed_url:
                st.audio(signed_url, format="audio/wav")
            else:
                st.warning("Audio playback link could not be generated.")
        else:
            st.warning("Audio file path not found.")

        col_a, col_b, col_c = st.columns(3)

        with col_a:
            if st.button("📝 Transcribe Now", key=f"transcribe_{recording_id}", use_container_width=True):
                st.session_state.selected_recording_id = recording_id
                st.switch_page("pages/04_Transcript_View.py")

        with col_b:
            if st.button("👁️ View Transcript", key=f"view_{recording_id}", use_container_width=True):
                st.session_state.selected_recording_id = recording_id
                st.switch_page("pages/04_Transcript_View.py")

        with col_c:
            if st.button("🗑️ Delete", key=f"delete_{recording_id}", use_container_width=True):
                try:
                    supabase.table("voice_recordings").delete().eq("id", recording_id).eq("user_id", user_id).execute()
                    st.success("Recording deleted.")
                    st.rerun()
                except Exception as e:
                    st.error(f"Delete failed: {e}")