import io
import uuid
import wave
from datetime import datetime, timezone

from utils.supabase_client import get_service_supabase_client


CHUNK_BUCKET = "voice-chunks"


def create_recording_session(user_id, title, category):
    supabase = get_service_supabase_client()

    record = {
        "user_id": user_id,
        "title": title,
        "category": category,
        "status": "recording",
    }

    result = supabase.table("recording_sessions").insert(record).execute()

    if result.data:
        return result.data[0]

    return None


def upload_wav_chunk(user_id, session_id, chunk_index, audio_frames, sample_rate):
    """
    audio_frames = list of bytes PCM frames
    """
    supabase = get_service_supabase_client()

    if not audio_frames:
        return False, "No audio frames to upload."

    chunk_id = str(uuid.uuid4())
    filename = f"chunk_{chunk_index:05d}_{chunk_id}.wav"
    storage_path = f"{user_id}/{session_id}/{filename}"

    wav_buffer = io.BytesIO()

    with wave.open(wav_buffer, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(b"".join(audio_frames))

    wav_bytes = wav_buffer.getvalue()

    try:
        supabase.storage.from_(CHUNK_BUCKET).upload(
            storage_path,
            wav_bytes,
            file_options={
                "content-type": "audio/wav",
                "upsert": "false",
            },
        )

        duration_seconds = round(len(b"".join(audio_frames)) / (sample_rate * 2), 2)

        supabase.table("recording_chunks").insert({
            "session_id": session_id,
            "user_id": user_id,
            "chunk_index": chunk_index,
            "storage_path": storage_path,
            "duration_seconds": duration_seconds,
        }).execute()

        supabase.table("recording_sessions").update({
            "updated_at": datetime.now(timezone.utc).isoformat()
        }).eq("id", session_id).execute()

        return True, storage_path

    except Exception as e:
        return False, str(e)


def finalize_recording_session(session_id):
    supabase = get_service_supabase_client()

    chunks = (
        supabase.table("recording_chunks")
        .select("*")
        .eq("session_id", session_id)
        .order("chunk_index")
        .execute()
    ).data or []

    total_duration = sum(float(c.get("duration_seconds") or 0) for c in chunks)

    result = supabase.table("recording_sessions").update({
        "status": "finalized",
        "total_duration_seconds": total_duration,
        "finalized_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }).eq("id", session_id).execute()

    return result.data[0] if result.data else None


from utils.supabase_client import get_service_supabase_client


def get_user_recording_sessions(user_id):
    supabase = get_service_supabase_client()

    result = (
        supabase.table("recording_sessions")
        .select("*")
        .eq("user_id", user_id)
        .order("created_at", desc=True)
        .execute()
    )

    return result.data or []


def get_session_chunks(session_id):
    supabase = get_service_supabase_client()

    result = (
        supabase.table("recording_chunks")
        .select("*")
        .eq("session_id", session_id)
        .order("chunk_index")
        .execute()
    )

    return result.data or []


def recover_recording_session(session_id):
    supabase = get_service_supabase_client()

    result = (
        supabase.table("recording_sessions")
        .update({"status": "recording"})
        .eq("id", session_id)
        .execute()
    )

    return result.data[0] if result.data else None


def delete_recording_session(session_id):
    supabase = get_service_supabase_client()

    supabase.table("recording_chunks").delete().eq("session_id", session_id).execute()
    result = supabase.table("recording_sessions").delete().eq("id", session_id).execute()

    return True

import io
from pydub import AudioSegment
from utils.audio_storage import BUCKET_NAME


def merge_session_chunks_to_voice_recording(user_id, session_id):
    supabase = get_service_supabase_client()

    session_response = (
        supabase.table("recording_sessions")
        .select("*")
        .eq("id", session_id)
        .eq("user_id", user_id)
        .single()
        .execute()
    )

    session = session_response.data

    if not session:
        return False, "Recording session not found.", None

    if session.get("linked_voice_recording_id"):
        return True, "Recording already prepared.", session.get("linked_voice_recording_id")

    chunks = get_session_chunks(session_id)

    if not chunks:
        return False, "No chunks found for this session.", None

    combined_audio = AudioSegment.empty()

    for chunk in chunks:
        storage_path = chunk.get("storage_path")

        if not storage_path:
            continue

        chunk_bytes = supabase.storage.from_(CHUNK_BUCKET).download(storage_path)

        if not chunk_bytes:
            continue

        audio_segment = AudioSegment.from_file(io.BytesIO(chunk_bytes), format="wav")
        combined_audio += audio_segment

    if len(combined_audio) == 0:
        return False, "Merged audio is empty.", None

    final_buffer = io.BytesIO()
    combined_audio.export(final_buffer, format="mp3", bitrate="64k")
    final_bytes = final_buffer.getvalue()

    final_filename = f"long_recording_{session_id}.mp3"
    final_storage_path = f"{user_id}/long_recordings/{final_filename}"

    supabase.storage.from_(BUCKET_NAME).upload(
        final_storage_path,
        final_bytes,
        file_options={
            "content-type": "audio/mpeg",
            "upsert": "true",
        },
    )

    duration_seconds = round(len(combined_audio) / 1000, 2)

    voice_record = {
        "user_id": user_id,
        "title": session.get("title") or "Untitled Long Recording",
        "category": session.get("category") or "Other",
        "audio_url": final_storage_path,
        "audio_filename": final_filename,
        "duration_seconds": duration_seconds,
        "transcription_status": "not_transcribed",
        "summary_status": "not_summarized",
    }

    inserted = supabase.table("voice_recordings").insert(voice_record).execute()

    if not inserted.data:
        return False, "Could not create final recording record.", None

    final_recording = inserted.data[0]

    supabase.table("recording_sessions").update({
        "final_audio_url": final_storage_path,
        "total_duration_seconds": duration_seconds,
        "linked_voice_recording_id": final_recording["id"],
        "status": "finalized",
    }).eq("id", session_id).execute()

    return True, "Long recording prepared successfully.", final_recording["id"]
