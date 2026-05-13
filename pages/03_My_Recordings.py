import streamlit as st
import pandas as pd

from utils.auth import require_login, logout_user
from utils.supabase_client import get_authenticated_client, get_service_supabase_client
from utils.audio_storage import create_signed_audio_url
from utils.chunk_storage import (
    get_user_recording_sessions,
    get_session_chunks,
    finalize_recording_session,
    delete_recording_session,
    merge_session_chunks_to_voice_recording,
)


st.set_page_config(
    page_title="My Recordings - VoiceScribe AI",
    page_icon="📁",
    layout="wide"
)

require_login()

st.title("📁 My Recordings")
st.write("Listen to saved recordings, recover unfinished long recordings, and transcribe whenever you are ready.")

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
service_supabase = get_service_supabase_client()

# =====================================================
# LOAD SHORT RECORDINGS
# =====================================================
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
    recordings = []


# =====================================================
# LOAD LONG RECORDING SESSIONS
# =====================================================
try:
    sessions = get_user_recording_sessions(user_id)
except Exception as e:
    st.error(f"Unable to load long recording sessions: {e}")
    sessions = []


if not recordings and not sessions:
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

    sessions = [
        s for s in sessions
        if search_lower in str(s.get("title", "")).lower()
        or search_lower in str(s.get("category", "")).lower()
        or search_lower in str(s.get("status", "")).lower()
    ]


unfinished_sessions = [s for s in sessions if s.get("status") == "recording"]
finalized_sessions = [s for s in sessions if s.get("status") == "finalized"]


# =====================================================
# SUMMARY
# =====================================================
st.write(
    f"Short recordings: **{len(recordings)}** | "
    f"Unfinished long recordings: **{len(unfinished_sessions)}** | "
    f"Finalized long recordings: **{len(finalized_sessions)}**"
)

st.divider()


# =====================================================
# UNFINISHED LONG RECORDINGS
# =====================================================
st.subheader("⚠️ Unfinished Long Recordings")

if not unfinished_sessions:
    st.success("No unfinished long recording sessions.")
else:
    for session in unfinished_sessions:
        session_id = session.get("id")
        chunks = get_session_chunks(session_id)
        total_duration = sum(float(c.get("duration_seconds") or 0) for c in chunks)

        with st.container(border=True):
            st.warning("Unfinished recording found.")
            st.write(f"**Title:** {session.get('title') or 'Untitled Recording'}")
            st.write(f"**Category:** {session.get('category') or 'Other'}")
            st.write(f"**Chunks Saved:** {len(chunks)}")
            st.write(f"**Approx. Saved Duration:** {round(total_duration / 60, 2)} minutes")
            st.write(f"**Started:** {session.get('created_at')}")
            st.write(f"**Last Updated:** {session.get('updated_at')}")

            col1, col2, col3 = st.columns(3)

            with col1:
                if st.button("▶️ Continue / Resume", key=f"resume_{session_id}", use_container_width=True):
                    st.session_state.active_recording_session_id = session_id
                    st.session_state.active_chunk_index = len(chunks)
                    st.switch_page("pages/02_New_Recording.py")

            with col2:
                if st.button("✅ Finalize Saved Chunks", key=f"finalize_{session_id}", use_container_width=True):
                    finalized = finalize_recording_session(session_id)
                    if finalized:
                        st.success("Recording finalized successfully.")
                        st.rerun()
                    else:
                        st.error("Could not finalize recording.")

            with col3:
                if st.button("🗑️ Delete Session", key=f"delete_session_{session_id}", use_container_width=True):
                    delete_recording_session(session_id)
                    st.warning("Session deleted.")
                    st.rerun()


st.divider()


# =====================================================
# FINALIZED LONG RECORDINGS
# =====================================================
st.subheader("🎙️ Long Recording Sessions")

if not finalized_sessions:
    st.info("No finalized long recording sessions yet.")
else:
    for session in finalized_sessions:
        session_id = session.get("id")
        chunks = get_session_chunks(session_id)

        with st.container(border=True):
            st.subheader(f"🎙️ {session.get('title') or 'Untitled Long Recording'}")
            st.write(f"**Category:** {session.get('category') or 'Other'}")
            st.write(f"**Status:** `{session.get('status')}`")
            st.write(f"**Chunks Saved:** {len(chunks)}")
            st.write(f"**Total Duration:** {round(float(session.get('total_duration_seconds') or 0) / 60, 2)} minutes")
            st.write(f"**Created:** {session.get('created_at')}")
            st.write(f"**Finalized:** {session.get('finalized_at')}")

            if chunks:
                with st.expander("View Saved Chunks"):
                    for c in chunks:
                        st.write(
                            f"Chunk {c.get('chunk_index')} — "
                            f"{c.get('duration_seconds')} seconds — "
                            f"`{c.get('storage_path')}`"
                        )

            col1, col2 = st.columns(2)

            with col1:

                if st.button("🧩 Prepare for Transcription", key=f"prepare_{session_id}", use_container_width=True):
                    with st.spinner("Merging saved chunks into one final audio file..."):
                        success, message, final_recording_id = merge_session_chunks_to_voice_recording(
                            user_id=user_id,
                            session_id=session_id
                        )

                    if not success:
                        st.error(message)
                    else:
                        st.success(message)
                        st.session_state.selected_recording_id = final_recording_id
                        st.session_state.selected_session_id = None
                        st.switch_page("pages/04_Transcript_View.py")

            with col2:
                if st.button("🗑️ Delete", key=f"delete_finalized_{session_id}", use_container_width=True):
                    delete_recording_session(session_id)
                    st.warning("Long recording session deleted.")
                    st.rerun()


st.divider()


# =====================================================
# SHORT RECORDINGS
# =====================================================
st.subheader("🎧 Short Recordings")

if not recordings:
    st.info("No short recordings saved yet.")
else:
    st.write(f"Total short recordings: **{len(recordings)}**")

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
                    st.session_state.selected_session_id = None
                    st.switch_page("pages/04_Transcript_View.py")

            with col_b:
                if st.button("👁️ View Transcript", key=f"view_{recording_id}", use_container_width=True):
                    st.session_state.selected_recording_id = recording_id
                    st.session_state.selected_session_id = None
                    st.switch_page("pages/04_Transcript_View.py")

            with col_c:
                if st.button("🗑️ Delete", key=f"delete_{recording_id}", use_container_width=True):
                    try:
                        supabase.table("voice_recordings").delete().eq("id", recording_id).eq("user_id", user_id).execute()
                        st.success("Recording deleted.")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Delete failed: {e}")