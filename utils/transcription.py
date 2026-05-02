import os
import tempfile
import subprocess
import requests
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

api_key = os.getenv("OPENAI_API_KEY")

if not api_key:
    raise ValueError("OPENAI_API_KEY is missing in .env")

client = OpenAI(api_key=api_key)


def transcribe_audio_from_url(signed_audio_url: str) -> tuple[bool, str]:
    try:
        response = requests.get(signed_audio_url, timeout=180)

        if response.status_code != 200:
            return False, f"Could not download audio. Status code: {response.status_code}"

        audio_bytes = response.content

        if not audio_bytes:
            return False, "Downloaded audio file is empty."

        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as input_file:
            input_file.write(audio_bytes)
            input_path = input_file.name

        output_path = input_path.replace(".wav", ".mp3")

        # Convert to clean mono MP3 for stable transcription
        command = [
            "ffmpeg",
            "-y",
            "-i", input_path,
            "-ac", "1",
            "-ar", "16000",
            "-b:a", "64k",
            output_path
        ]

        subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True
        )

        with open(output_path, "rb") as audio_file:
            transcript = client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file
            )

        text = getattr(transcript, "text", "")

        if not text or not text.strip():
            return False, "Transcription returned empty text."

        return True, text.strip()

    except subprocess.CalledProcessError as e:
        return False, f"FFmpeg conversion failed: {e.stderr.decode(errors='ignore')}"

    except Exception as e:
        return False, f"Transcription failed: {str(e)}"