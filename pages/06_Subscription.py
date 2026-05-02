import streamlit as st
from utils.auth import require_login, logout_user
from utils.supabase_client import get_authenticated_client
from utils.subscription import get_or_create_subscription, calculate_remaining_minutes
from utils.payment_storage import upload_payment_receipt


st.set_page_config(
    page_title="Subscription - VoiceScribe AI",
    page_icon="💳",
    layout="wide"
)

require_login()

st.title("💳 Subscription")
st.write("Choose a plan, make payment, and upload your payment evidence for admin approval.")

with st.sidebar:
    st.write("VoiceScribe AI")
    if st.button("Logout"):
        logout_user()

profile = st.session_state.get("profile")
user_id = profile.get("id") if profile else None

if not user_id:
    st.error("User profile not found. Please logout and login again.")
    st.stop()

supabase = get_authenticated_client()

subscription = get_or_create_subscription(user_id)
remaining = calculate_remaining_minutes(subscription)

st.subheader("Current Plan")

c1, c2, c3 = st.columns(3)
c1.metric("Plan", subscription.get("plan_name", "Free"))
c2.metric("Allowed Minutes", subscription.get("transcription_minutes", 0))
c3.metric("Remaining Minutes", round(remaining, 2))

st.divider()

plans = {
    "Basic": {"amount": 5000, "minutes": 300},
    "Pro": {"amount": 10000, "minutes": 1000},
    "Premium": {"amount": 25000, "minutes": 3000},
}

st.subheader("Available Plans")

selected_plan = st.selectbox("Select Plan", list(plans.keys()))
plan = plans[selected_plan]

st.info(
    f"""
    **{selected_plan} Plan**

    Amount: ₦{plan['amount']:,}  
    Transcription Minutes: {plan['minutes']} minutes
    """
)

st.subheader("Payment Instruction")

st.write("""
Make payment to the account below and upload your receipt.

**Bank:** Your Bank Name  
**Account Name:** VoiceScribe AI / Chumcred Limited  
**Account Number:** 0000000000
""")

payment_reference = st.text_input("Payment Reference / Narration")
uploaded_file = st.file_uploader(
    "Upload Payment Evidence",
    type=["png", "jpg", "jpeg", "pdf"]
)

if st.button("Submit Payment Evidence", use_container_width=True):
    if not payment_reference:
        st.error("Please enter payment reference.")
        st.stop()

    if not uploaded_file:
        st.error("Please upload payment evidence.")
        st.stop()

    success, message, receipt_path = upload_payment_receipt(uploaded_file)

    if not success:
        st.error(f"Receipt upload failed: {message}")
        st.stop()

    payment_record = {
        "user_id": user_id,
        "plan_name": selected_plan,
        "amount": plan["amount"],
        "payment_reference": payment_reference,
        "receipt_url": receipt_path,
        "status": "pending",
    }

    try:
        supabase.table("subscription_payments").insert(payment_record).execute()
        st.success("Payment evidence submitted successfully. Admin will review and approve.")
    except Exception as e:
        st.error(f"Could not save payment record: {e}")

st.divider()

st.subheader("My Payment History")

try:
    payments = (
        supabase.table("subscription_payments")
        .select("*")
        .eq("user_id", user_id)
        .order("created_at", desc=True)
        .execute()
    ).data or []

    if not payments:
        st.info("No payment history yet.")
    else:
        for p in payments:
            with st.container(border=True):
                st.write(f"**Plan:** {p.get('plan_name')}")
                st.write(f"**Amount:** ₦{float(p.get('amount') or 0):,.2f}")
                st.write(f"**Reference:** {p.get('payment_reference')}")
                st.write(f"**Status:** `{p.get('status')}`")
                st.write(f"**Submitted:** {p.get('created_at')}")
                if p.get("admin_note"):
                    st.write(f"**Admin Note:** {p.get('admin_note')}")

except Exception as e:
    st.error(f"Unable to load payment history: {e}")