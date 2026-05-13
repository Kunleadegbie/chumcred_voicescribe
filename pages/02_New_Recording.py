import io
import time
import av
import numpy as np
import streamlit as st
from audiorecorder import audiorecorder
from streamlit_webrtc import webrtc_streamer, WebRtcMode

from utils.auth import require_login, logout_user
from utils.supabase_client import get_service_supabase_client
from utils.audio_storage import upload_audio_to_supabase
from utils.chunk_storage import (
    create_recording_session,
    upload_wav_chunk,
    finalize_recording_session,
)


st.set_page_config(
    page_title="New Recording - VoiceScribe AI",
    page_icon="🎙️",
    layout="wide"
)

require_login()

st.title("🎙️ New Recording")
st.write("Record meetings, church messages, lectures, interviews, or personal notes.")

with st.sidebar:
    st.write("VoiceScribe AI")
    if st.button("Logout"):
        logout_user()

user = st.session_state.get("user")

if not user:
    st.error("User session not found. Please login again.")
    st.stop()

supabase = get_service_supabase_client()

profile_response = (
    supabase.table("user_profiles")
    .select("*")
    .eq("auth_user_id", user.id)
    .single()
    .execute()
)

profile = profile_response.data

if not profile:
    st.error("User profile not found. Please logout and login again.")
    st.stop()

user_id = profile["id"]

# =====================================================
# SESSION STATE
# =====================================================
if "unsaved_audio_bytes" not in st.session_state:
    st.session_state.unsaved_audio_bytes = None

if "unsaved_audio_duration" not in st.session_state:
    st.session_state.unsaved_audio_duration = 0

if "unsaved_recording_available" not in st.session_state:
    st.session_state.unsaved_recording_available = False

if "active_recording_session_id" not in st.session_state:
    st.session_state.active_recording_session_id = None

if "active_chunk_index" not in st.session_state:
    st.session_state.active_chunk_index = 0


st.divider()

col1, col2 = st.columns([2, 1])

with col1:
    title = st.text_input(
        "Recording Title",
        placeholder="Example: Sunday Message - Faith and Obedience",
        key="recording_title"
    )

with col2:
    category = st.selectbox(
        "Category",
        [
            "Meeting",
            "Church Message",
            "Lecture",
            "Interview",
            "Personal Note",
            "Training",
            "Other"
        ],
        key="recording_category"
    )

recording_mode = st.radio(
    "Select Recording Mode",
    [
        "Short Recording (quick notes under 10 minutes)",
        "Long Recording (sermons, meetings, lectures)"
    ],
    horizontal=True
)

# =====================================================
# SHORT RECORDING MODE - EXISTING FLOW
# =====================================================
if recording_mode == "Short Recording (quick notes under 10 minutes)":
    st.info("Click Start to begin recording. Click Stop when you are done.")

    audio = audiorecorder("🎙️ Start Recording", "⏹️ Stop Recording")

    if len(audio) > 0:
        st.success("Recording captured successfully.")

        wav_buffer_preview = io.BytesIO()
        audio.export(wav_buffer_preview, format="wav")
        preview_bytes = wav_buffer_preview.getvalue()

        st.session_state.unsaved_audio_bytes = preview_bytes
        st.session_state.unsaved_audio_duration = round(len(audio) / 1000, 2)
        st.session_state.unsaved_recording_available = True

    if st.session_state.unsaved_recording_available and st.session_state.unsaved_audio_bytes:
        st.warning("You have an unsaved recording. Save it before leaving or starting another important recording.")

        st.subheader("Playback")
        st.audio(st.session_state.unsaved_audio_bytes, format="audio/wav")

        duration_seconds = st.session_state.unsaved_audio_duration
        st.write(f"Duration: **{duration_seconds} seconds**")

        st.divider()
        st.subheader("Save Recording")

        col_save, col_clear = st.columns([2, 1])

        with col_save:
            if st.button("💾 Save Recording", use_container_width=True):
                if not title:
                    st.error("Please enter a recording title before saving.")
                    st.stop()

                success, message, upload_data = upload_audio_to_supabase(
                    st.session_state.unsaved_audio_bytes,
                    "wav"
                )

                if not success:
                    st.error(f"Upload failed: {message}")
                    st.stop()

                record = {
                    "user_id": user_id,
                    "title": title,
                    "category": category,
                    "audio_url": upload_data["storage_path"],
                    "audio_filename": upload_data["filename"],
                    "duration_seconds": duration_seconds,
                    "transcription_status": "not_transcribed",
                    "summary_status": "not_summarized",
                }

                try:
                    result = supabase.table("voice_recordings").insert(record).execute()

                    if not result.data:
                        st.error("Database insert failed. No record was returned.")
                        st.stop()

                    saved_record = result.data[0]

                    st.session_state.unsaved_audio_bytes = None
                    st.session_state.unsaved_audio_duration = 0
                    st.session_state.unsaved_recording_available = False

                    st.success("Recording saved successfully.")
                    st.write(f"Saved Recording ID: `{saved_record['id']}`")

                    col_a, col_b, col_c = st.columns(3)

                    with col_a:
                        if st.button("🎧 Go to My Recordings", use_container_width=True):
                            st.switch_page("pages/03_My_Recordings.py")

                    with col_b:
                        if st.button("📝 Transcribe Now", use_container_width=True):
                            st.session_state.selected_recording_id = saved_record["id"]
                            st.switch_page("pages/04_Transcript_View.py")

                    with col_c:
                        if st.button("📁 Transcribe Later", use_container_width=True):
                            st.switch_page("pages/03_My_Recordings.py")

                except Exception as e:
                    st.error(f"Database save failed: {e}")

        with col_clear:
            if st.button("🗑️ Clear Unsaved Recording", use_container_width=True):
                st.session_state.unsaved_audio_bytes = None
                st.session_state.unsaved_audio_duration = 0
                st.session_state.unsaved_recording_available = False
                st.success("Unsaved recording cleared.")
                st.rerun()

    else:
        st.warning("No recording yet.")

# =====================================================
# LONG RECORDING MODE - CHUNKED FLOW
# =====================================================
else:
    st.info(
        "Long Recording Mode saves your audio in small chunks. "
        "This is recommended for sermons, long meetings, and lectures."
    )

    class AudioChunkProcessor:
        def __init__(self):
            self.frames = []
            self.sample_rate = 48000
            self.last_upload_time = time.time()
            self.chunk_seconds = 30

        def recv(self, frame: av.AudioFrame) -> av.AudioFrame:
            session_id = st.session_state.get("active_recording_session_id")

            if not session_id:
                return frame

            pcm = frame.to_ndarray()

            if pcm.ndim > 1:
                pcm = pcm.mean(axis=0)

            pcm = pcm.astype(np.int16).tobytes()

            self.sample_rate = frame.sample_rate
            self.frames.append(pcm)

            now = time.time()

            if now - self.last_upload_time >= self.chunk_seconds:
                chunk_index = st.session_state.get("active_chunk_index", 0) + 1
                st.session_state.active_chunk_index = chunk_index

                upload_wav_chunk(
                    user_id=user_id,
                    session_id=session_id,
                    chunk_index=chunk_index,
                    audio_frames=self.frames,
                    sample_rate=self.sample_rate,
                )

                self.frames = []
                self.last_upload_time = now

            return frame

    st.subheader("Step 1: Create Recording Session")

    if not st.session_state.active_recording_session_id:
        if st.button("🎙️ Create Recording Session", use_container_width=True):
            if not title:
                st.error("Please enter a recording title first.")
                st.stop()

            session = create_recording_session(user_id, title, category)

            if session:
                st.session_state.active_recording_session_id = session["id"]
                st.session_state.active_chunk_index = 0
                st.success("Recording session created. Now start the recorder below.")
                st.rerun()
            else:
                st.error("Could not create recording session.")
    else:
        st.success("🎙️ Live Recording Session Active")

        session_title = title if title else "Untitled Recording"

        st.markdown(
            f"""
            **Title:** {session_title}  
            **Category:** {category}  
            **Status:** Auto-saving audio every 30 seconds
            """
        )

    st.divider()
    st.subheader("Step 2: Record Audio")

    if st.session_state.active_recording_session_id:
        st.warning("Click START below. Audio chunks will auto-save every 30 seconds.")

        webrtc_streamer(
            key="voicescribe-long-recorder",
            mode=WebRtcMode.SENDONLY,
            audio_processor_factory=AudioChunkProcessor,
            media_stream_constraints={
                "audio": True,
                "video": False,
            },
            async_processing=True,
        )

        st.info("Do not close the browser while recording. Saved chunks will remain recoverable.")

        st.divider()

        col_a, col_b = st.columns(2)

        with col_a:
            if st.button("✅ Finalize Recording", use_container_width=True):
                session_id = st.session_state.active_recording_session_id

                finalized = finalize_recording_session(session_id)

                if finalized:
                    st.success("Recording finalized successfully.")
                    st.session_state.active_recording_session_id = None
                    st.session_state.active_chunk_index = 0
                    st.switch_page("pages/03_My_Recordings.py")
                else:
                    st.error("Could not finalize recording.")

        with col_b:
            if st.button("🗑️ Cancel Session", use_container_width=True):
                st.session_state.active_recording_session_id = None
                st.session_state.active_chunk_index = 0
                st.warning("Recording session removed from this page. Existing uploaded chunks remain in Supabase.")

    else:
        st.info("Create a recording session first.")