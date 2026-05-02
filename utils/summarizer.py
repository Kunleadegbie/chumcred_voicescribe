import os
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def summarize_transcript(transcript_text: str, category: str = "Other") -> tuple[bool, dict]:
    try:
        prompt = f"""
You are VoiceScribe AI.

Summarize the transcript below.

Category: {category}

Return the result in this structure:

SUMMARY:
A clear summary.

KEY POINTS:
- Point 1
- Point 2
- Point 3

ACTION ITEMS:
- Action 1
- Action 2
- If none, write "No specific action items."

TRANSCRIPT:
{transcript_text}
"""

        response = client.responses.create(
            model="gpt-5.2",
            input=prompt
        )

        output = response.output_text

        summary = output
        key_points = ""
        action_items = ""

        if "KEY POINTS:" in output:
            summary = output.split("KEY POINTS:")[0].replace("SUMMARY:", "").strip()
            rest = output.split("KEY POINTS:")[1]

            if "ACTION ITEMS:" in rest:
                key_points = rest.split("ACTION ITEMS:")[0].strip()
                action_items = rest.split("ACTION ITEMS:")[1].strip()
            else:
                key_points = rest.strip()

        return True, {
            "summary_text": summary,
            "key_points": key_points,
            "action_items": action_items
        }

    except Exception as e:
        return False, {
            "summary_text": str(e),
            "key_points": "",
            "action_items": ""
        }