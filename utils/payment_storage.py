import uuid
from datetime import datetime
import streamlit as st
from utils.supabase_client import get_authenticated_client

BUCKET_NAME = "payment-receipts"


def upload_payment_receipt(file):
    supabase = get_authenticated_client()

    user = st.session_state.get("user")
    if not user:
        return False, "User session not found.", None

    auth_user_id = user.id
    ext = file.name.split(".")[-1].lower()
    receipt_id = str(uuid.uuid4())
    timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")

    filename = f"{receipt_id}_{timestamp}.{ext}"
    storage_path = f"{auth_user_id}/{filename}"

    try:
        supabase.storage.from_(BUCKET_NAME).upload(
            storage_path,
            file.getvalue(),
            file_options={
                "content-type": file.type,
                "upsert": "false"
            }
        )

        return True, "Receipt uploaded successfully.", storage_path

    except Exception as e:
        return False, str(e), None