import streamlit as st
import pandas as pd

from utils.auth import require_login, logout_user
from utils.supabase_client import get_authenticated_client
from utils.audio_storage import create_signed_audio_url


st.set_page_config(
    page_title="Search Archive - VoiceScribe AI",
    page_icon="🔍",
    layout="wide"
)

require_login()

st.title("🔍 Search Archive")
st.write("Search your saved recordings, transcripts, summaries, key points, and action items.")

with st.sidebar:
    st.write("VoiceScribe AI")
    if st.button("Logout"):
        logout_user()

profile = st.session_state.get("profile")
user_id = profile.get("id") if profile else None

if not user_id:
    st.error("User profile not found. Please logout and login again.")
    st.stop()

supabase = get_authenticated_client()

search_query = st.text_input(
    "Search",
    placeholder="Example: faith, board meeting, customer complaint, action items..."
)

category_filter = st.selectbox(
    "Filter by Category",
    [
        "All",
        "Meeting",
        "Church Message",
        "Lecture",
        "Interview",
        "Personal Note",
        "Training",
        "Other"
    ]
)

status_filter = st.selectbox(
    "Filter by Transcription Status",
    [
        "All",
        "transcribed",
        "not_transcribed"
    ]
)

try:
    rec_response = (
        supabase.table("voice_recordings")
        .select("*")
        .eq("user_id", user_id)
        .order("created_at", desc=True)
        .execute()
    )

    recordings = rec_response.data or []

    trans_response = (
        supabase.table("voice_transcripts")
        .select("*")
        .eq("user_id", user_id)
        .execute()
    )

    transcripts = trans_response.data or []

except Exception as e:
    st.error(f"Unable to load archive: {e}")
    st.stop()


transcript_map = {
    t.get("recording_id"): t
    for t in transcripts
}

combined_records = []

for rec in recordings:
    transcript = transcript_map.get(rec.get("id"), {})

    combined_records.append({
        "recording_id": rec.get("id"),
        "title": rec.get("title", ""),
        "category": rec.get("category", ""),
        "duration_seconds": rec.get("duration_seconds", 0),
        "transcription_status": rec.get("transcription_status", ""),
        "summary_status": rec.get("summary_status", ""),
        "created_at": rec.get("created_at", ""),
        "audio_url": rec.get("audio_url", ""),
        "transcript_text": transcript.get("transcript_text", ""),
        "summary_text": transcript.get("summary_text", ""),
        "key_points": transcript.get("key_points", ""),
        "action_items": transcript.get("action_items", ""),
    })


if category_filter != "All":
    combined_records = [
        r for r in combined_records
        if r.get("category") == category_filter
    ]

if status_filter != "All":
    combined_records = [
        r for r in combined_records
        if r.get("transcription_status") == status_filter
    ]

if search_query:
    q = search_query.lower()

    combined_records = [
        r for r in combined_records
        if q in str(r.get("title", "")).lower()
        or q in str(r.get("category", "")).lower()
        or q in str(r.get("transcript_text", "")).lower()
        or q in str(r.get("summary_text", "")).lower()
        or q in str(r.get("key_points", "")).lower()
        or q in str(r.get("action_items", "")).lower()
    ]


st.divider()

st.write(f"Search results: **{len(combined_records)}**")

if not combined_records:
    st.info("No matching recordings found.")
    st.stop()


for item in combined_records:
    recording_id = item.get("recording_id")

    with st.container(border=True):
        col1, col2 = st.columns([3, 1])

        with col1:
            st.subheader(f"🎧 {item.get('title') or 'Untitled Recording'}")
            st.write(f"**Category:** {item.get('category')}")
            st.write(f"**Created:** {item.get('created_at')}")
            st.write(f"**Duration:** {item.get('duration_seconds')} seconds")

        with col2:
            st.write(f"**Transcript:** `{item.get('transcription_status')}`")
            st.write(f"**Summary:** `{item.get('summary_status')}`")

        audio_path = item.get("audio_url")

        if audio_path:
            signed_url = create_signed_audio_url(audio_path)
            if signed_url:
                st.audio(signed_url, format="audio/wav")

        if item.get("summary_text"):
            st.markdown("### Summary")
            st.write(item.get("summary_text"))

        if item.get("key_points"):
            with st.expander("View Key Points"):
                st.write(item.get("key_points"))

        if item.get("action_items"):
            with st.expander("View Action Items"):
                st.write(item.get("action_items"))

        if item.get("transcript_text"):
            with st.expander("View Full Transcript"):
                st.text_area(
                    "Transcript",
                    item.get("transcript_text"),
                    height=250,
                    key=f"transcript_{recording_id}"
                )

        col_a, col_b = st.columns(2)

        with col_a:
            if st.button("👁️ Open Transcript", key=f"open_{recording_id}", use_container_width=True):
                st.session_state.selected_recording_id = recording_id
                st.switch_page("pages/04_Transcript_View.py")

        with col_b:
            if item.get("transcription_status") != "transcribed":
                if st.button("📝 Transcribe Now", key=f"transcribe_{recording_id}", use_container_width=True):
                    st.session_state.selected_recording_id = recording_id
                    st.switch_page("pages/04_Transcript_View.py")
            else:
                st.success("Already transcribed")