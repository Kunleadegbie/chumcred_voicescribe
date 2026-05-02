import uuid
from datetime import datetime
import streamlit as st
from utils.supabase_client import get_service_supabase_client

BUCKET_NAME = "voice-recordings"


def upload_audio_to_supabase(audio_bytes: bytes, file_extension: str = "wav"):
    supabase = get_service_supabase_client()

    user = st.session_state.get("user")

    if not user:
        return False, "User session not found.", None

    auth_user_id = user.id
    recording_uuid = str(uuid.uuid4())
    timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")

    filename = f"{recording_uuid}_{timestamp}.{file_extension}"
    storage_path = f"{auth_user_id}/{filename}"

    try:
        supabase.storage.from_(BUCKET_NAME).upload(
            storage_path,
            audio_bytes,
            file_options={
                "content-type": f"audio/{file_extension}",
                "upsert": "false"
            }
        )

        return True, "Audio uploaded successfully.", {
            "storage_path": storage_path,
            "filename": filename
        }

    except Exception as e:
        return False, str(e), None


def create_signed_audio_url(storage_path: str, expires_in: int = 3600):
    supabase = get_service_supabase_client()

    try:
        result = supabase.storage.from_(BUCKET_NAME).create_signed_url(
            storage_path,
            expires_in
        )

        return result.get("signedURL") or result.get("signedUrl")

    except Exception:
        return None