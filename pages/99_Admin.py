from datetime import datetime, timezone, timedelta
import streamlit as st

from utils.auth import require_login, logout_user
from utils.supabase_client import get_authenticated_client


st.set_page_config(
    page_title="Admin - VoiceScribe AI",
    page_icon="🛡️",
    layout="wide"
)

require_login()

st.title("🛡️ Admin Dashboard")

with st.sidebar:
    st.write("VoiceScribe AI")
    if st.button("Logout"):
        logout_user()

profile = st.session_state.get("profile")
admin_user_id = profile.get("id") if profile else None
role = profile.get("role") if profile else "user"

if role != "admin":
    st.error("Access denied. Admin only.")
    st.stop()

supabase = get_authenticated_client()

PLAN_MINUTES = {
    "Basic": 300,
    "Pro": 1000,
    "Premium": 3000,
}

st.subheader("Pending Payment Approvals")

try:
    payments = (
        supabase.table("subscription_payments")
        .select("*")
        .eq("status", "pending")
        .order("created_at", desc=True)
        .execute()
    ).data or []
except Exception as e:
    st.error(f"Unable to load pending payments: {e}")
    st.stop()

if not payments:
    st.info("No pending payment approvals.")
else:
    for p in payments:
        payment_id = p.get("id")
        user_id = p.get("user_id")
        plan_name = p.get("plan_name")
        minutes = PLAN_MINUTES.get(plan_name, 30)

        with st.container(border=True):
            st.write(f"**Plan:** {plan_name}")
            st.write(f"**Amount:** ₦{float(p.get('amount') or 0):,.2f}")
            st.write(f"**Reference:** {p.get('payment_reference')}")
            st.write(f"**Submitted:** {p.get('created_at')}")
            st.write(f"**Receipt Path:** `{p.get('receipt_url')}`")

            admin_note = st.text_area(
                "Admin Note",
                key=f"note_{payment_id}",
                placeholder="Optional approval/rejection note"
            )

            col1, col2 = st.columns(2)

            with col1:
                if st.button("✅ Approve", key=f"approve_{payment_id}", use_container_width=True):
                    try:
                        end_date = datetime.now(timezone.utc) + timedelta(days=30)

                        existing_sub = (
                            supabase.table("subscriptions")
                            .select("*")
                            .eq("user_id", user_id)
                            .eq("status", "active")
                            .execute()
                        ).data

                        if existing_sub:
                            sub_id = existing_sub[0]["id"]
                            supabase.table("subscriptions").update({
                                "plan_name": plan_name,
                                "transcription_minutes": minutes,
                                "used_minutes": 0,
                                "status": "active",
                                "end_date": end_date.isoformat(),
                            }).eq("id", sub_id).execute()
                        else:
                            supabase.table("subscriptions").insert({
                                "user_id": user_id,
                                "plan_name": plan_name,
                                "transcription_minutes": minutes,
                                "used_minutes": 0,
                                "status": "active",
                                "end_date": end_date.isoformat(),
                            }).execute()

                        supabase.table("subscription_payments").update({
                            "status": "approved",
                            "admin_note": admin_note,
                            "approved_by": admin_user_id,
                            "approved_at": datetime.now(timezone.utc).isoformat(),
                        }).eq("id", payment_id).execute()

                        st.success("Payment approved and subscription activated.")
                        st.rerun()

                    except Exception as e:
                        st.error(f"Approval failed: {e}")

            with col2:
                if st.button("❌ Reject", key=f"reject_{payment_id}", use_container_width=True):
                    try:
                        supabase.table("subscription_payments").update({
                            "status": "rejected",
                            "admin_note": admin_note,
                        }).eq("id", payment_id).execute()

                        st.warning("Payment rejected.")
                        st.rerun()

                    except Exception as e:
                        st.error(f"Rejection failed: {e}")