import streamlit as st

from utils.auth import require_login, logout_user
from utils.supabase_client import get_authenticated_client
from utils.audio_storage import create_signed_audio_url
from utils.transcription import transcribe_audio_from_url
from utils.summarizer import summarize_transcript
from utils.subscription import update_used_minutes, get_or_create_subscription, calculate_remaining_minutes


st.set_page_config(
    page_title="Transcript View - VoiceScribe AI",
    page_icon="📝",
    layout="wide"
)

require_login()

st.title("📝 Transcript View")

with st.sidebar:
    st.write("VoiceScribe AI")
    if st.button("Logout"):
        logout_user()

recording_id = st.session_state.get("selected_recording_id")

if not recording_id:
    st.warning("No recording selected.")
    st.page_link("pages/03_My_Recordings.py", label="Back to My Recordings")
    st.stop()

profile = st.session_state.get("profile")
user_id = profile.get("id") if profile else None

if not user_id:
    st.error("User profile not found. Please logout and login again.")
    st.stop()

supabase = get_authenticated_client()

try:
    rec_response = (
        supabase.table("voice_recordings")
        .select("*")
        .eq("id", recording_id)
        .eq("user_id", user_id)
        .single()
        .execute()
    )
    recording = rec_response.data
except Exception as e:
    st.error(f"Unable to load recording: {e}")
    st.stop()

if not recording:
    st.error("Recording not found.")
    st.stop()

st.subheader(recording.get("title", "Untitled Recording"))
st.write(f"**Category:** {recording.get('category', 'Other')}")
st.write(f"**Transcription Status:** `{recording.get('transcription_status')}`")
st.write(f"**Summary Status:** `{recording.get('summary_status')}`")

audio_path = recording.get("audio_url")

signed_url = None
if audio_path:
    signed_url = create_signed_audio_url(audio_path)
    if signed_url:
        st.audio(signed_url, format="audio/wav")
    else:
        st.warning("Audio playback link could not be generated.")
else:
    st.warning("Audio file path not found.")

st.divider()

try:
    existing_transcript = (
        supabase.table("voice_transcripts")
        .select("*")
        .eq("recording_id", recording_id)
        .eq("user_id", user_id)
        .execute()
    )
    transcript_data = existing_transcript.data[0] if existing_transcript.data else None
except Exception as e:
    st.error(f"Unable to load transcript: {e}")
    st.stop()

if transcript_data:
    st.success("Transcript already available.")

    st.subheader("AI Summary")
    st.write(transcript_data.get("summary_text") or "No summary yet.")

    st.subheader("Key Points")
    st.write(transcript_data.get("key_points") or "No key points yet.")

    st.subheader("Action Items")
    st.write(transcript_data.get("action_items") or "No action items yet.")

    st.subheader("Full Transcript")
    st.text_area(
        "Transcript",
        transcript_data.get("transcript_text", ""),
        height=350
    )

else:
    st.info("This recording has not been transcribed yet.")

    subscription = get_or_create_subscription(user_id)
    remaining_minutes = calculate_remaining_minutes(subscription)
    duration_minutes = round(float(recording.get("duration_seconds") or 0) / 60, 2)

    st.write(f"**Required Minutes:** {duration_minutes}")
    st.write(f"**Available Minutes:** {round(remaining_minutes, 2)}")

    if st.button("📝 Transcribe and Summarize Now", use_container_width=True):
        if remaining_minutes < duration_minutes:
            st.error(
                f"You do not have enough transcription minutes. "
                f"Required: {duration_minutes} mins, Available: {round(remaining_minutes, 2)} mins."
            )
            st.stop()

        if not signed_url:
            st.error("Audio file could not be accessed.")
            st.stop()

        with st.spinner("Transcribing audio..."):
            success, transcript_text = transcribe_audio_from_url(signed_url)

        if not success:
            st.error(f"Transcription failed: {transcript_text}")
            st.stop()

        with st.spinner("Generating AI summary..."):
            sum_success, summary_data = summarize_transcript(
                transcript_text,
                recording.get("category", "Other")
            )

        if not sum_success:
            st.error(f"Summary failed: {summary_data.get('summary_text')}")
            st.stop()

        transcript_record = {
            "recording_id": recording_id,
            "user_id": user_id,
            "transcript_text": transcript_text,
            "summary_text": summary_data.get("summary_text"),
            "key_points": summary_data.get("key_points"),
            "action_items": summary_data.get("action_items"),
        }

        try:
            supabase.table("voice_transcripts").insert(transcript_record).execute()

            supabase.table("voice_recordings").update({
                "transcription_status": "transcribed",
                "summary_status": "summarized"
            }).eq("id", recording_id).eq("user_id", user_id).execute()

            update_used_minutes(user_id, recording.get("duration_seconds", 0))

            st.success("Transcription and summary completed.")
            st.rerun()

        except Exception as e:
            st.error(f"Unable to save transcript: {e}")

st.divider()

if st.button("⬅️ Back to My Recordings"):
    st.switch_page("pages/03_My_Recordings.py")