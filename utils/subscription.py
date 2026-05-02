from datetime import datetime, timedelta, timezone
from utils.supabase_client import get_authenticated_client


def get_or_create_subscription(user_id):
    supabase = get_authenticated_client()

    existing = (
        supabase.table("subscriptions")
        .select("*")
        .eq("user_id", user_id)
        .eq("status", "active")
        .execute()
    )

    if existing.data:
        return existing.data[0]

    end_date = datetime.now(timezone.utc) + timedelta(days=30)

    new_sub = {
        "user_id": user_id,
        "plan_name": "Free",
        "transcription_minutes": 30,
        "used_minutes": 0,
        "status": "active",
        "end_date": end_date.isoformat(),
    }

    created = supabase.table("subscriptions").insert(new_sub).execute()
    return created.data[0] if created.data else None


def calculate_remaining_minutes(subscription):
    if not subscription:
        return 0

    total = float(subscription.get("transcription_minutes") or 0)
    used = float(subscription.get("used_minutes") or 0)

    return max(total - used, 0)


def update_used_minutes(user_id, duration_seconds):
    supabase = get_authenticated_client()

    subscription = get_or_create_subscription(user_id)

    if not subscription:
        return False, "Subscription not found."

    used_minutes = float(subscription.get("used_minutes") or 0)
    additional_minutes = round(float(duration_seconds or 0) / 60, 2)

    new_used_minutes = used_minutes + additional_minutes

    supabase.table("subscriptions").update({
        "used_minutes": new_used_minutes
    }).eq("id", subscription["id"]).execute()

    return True, new_used_minutes