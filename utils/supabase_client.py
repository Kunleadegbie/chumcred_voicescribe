import os
import streamlit as st
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

@st.cache_resource
def get_service_supabase_client() -> Client:
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

    if not url or not key:
        st.error("SUPABASE_SERVICE_ROLE_KEY is missing.")
        st.stop()

    return create_client(url, key)

@st.cache_resource
def get_supabase_client() -> Client:
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_ANON_KEY")

    if not url or not key:
        st.error("SUPABASE_URL or SUPABASE_ANON_KEY is missing in environment variables.")
        st.stop()

    return create_client(url, key)


def get_authenticated_client() -> Client:
    supabase = get_supabase_client()

    access_token = st.session_state.get("access_token")
    refresh_token = st.session_state.get("refresh_token")

    if access_token and refresh_token:
        try:
            supabase.auth.set_session(access_token, refresh_token)
        except Exception:
            pass

    return supabase

