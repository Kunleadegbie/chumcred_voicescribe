import streamlit as st
from utils.supabase_client import get_supabase_client


def init_session():
    defaults = {
        "logged_in": False,
        "user": None,
        "profile": None,
        "access_token": None,
        "refresh_token": None,
    }

    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def signup_user(email, password, full_name):
    supabase = get_supabase_client()

    try:
        result = supabase.auth.sign_up({
            "email": email,
            "password": password,
            "options": {
                "data": {
                    "full_name": full_name
                }
            }
        })

        user = result.user

        if user:
            return True, "Registration successful. Please check your email to confirm your account before logging in."

        return False, "Registration could not be completed."

    except Exception as e:
        return False, str(e)


def login_user(email, password):
    supabase = get_supabase_client()

    try:
        result = supabase.auth.sign_in_with_password({
            "email": email,
            "password": password
        })

        if not result.user:
            return False, "Invalid login details."

        st.session_state.logged_in = True
        st.session_state.user = result.user
        st.session_state.access_token = result.session.access_token
        st.session_state.refresh_token = result.session.refresh_token

        create_or_get_profile(result.user)

        return True, "Login successful."

    except Exception as e:
        return False, str(e)


def create_or_get_profile(user):
    supabase = get_supabase_client()

    email = user.email
    auth_user_id = user.id
    full_name = ""

    if user.user_metadata:
        full_name = user.user_metadata.get("full_name", "")

    existing = supabase.table("user_profiles").select("*").eq("auth_user_id", auth_user_id).execute()

    if existing.data:
        st.session_state.profile = existing.data[0]
        return existing.data[0]

    profile_data = {
        "auth_user_id": auth_user_id,
        "email": email,
        "full_name": full_name,
        "role": "user",
        "status": "active",
    }

    created = supabase.table("user_profiles").insert(profile_data).execute()

    if created.data:
        st.session_state.profile = created.data[0]
        return created.data[0]

    return None


def logout_user():
    supabase = get_supabase_client()

    try:
        supabase.auth.sign_out()
    except Exception:
        pass

    st.session_state.logged_in = False
    st.session_state.user = None
    st.session_state.profile = None
    st.session_state.access_token = None
    st.session_state.refresh_token = None

    st.rerun()


def require_login():
    init_session()

    if not st.session_state.logged_in:
        st.warning("Please login to continue.")
        st.stop()