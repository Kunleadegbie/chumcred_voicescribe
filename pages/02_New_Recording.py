import io
import streamlit as st
from audiorecorder import audiorecorder

from utils.auth import require_login, logout_user
from utils.supabase_client import get_service_supabase_client
from utils.audio_storage import upload_audio_to_supabase


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
# KEEP UNSAVED RECORDING DURING SESSION
# =====================================================
if "unsaved_audio_bytes" not in st.session_state:
    st.session_state.unsaved_audio_bytes = None

if "unsaved_audio_duration" not in st.session_state:
    st.session_state.unsaved_audio_duration = 0

if "unsaved_recording_available" not in st.session_state:
    st.session_state.unsaved_recording_available = False

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