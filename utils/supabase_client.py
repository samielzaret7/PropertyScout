"""
Supabase connection — initialised once per session via @st.cache_resource.
Falls back to python-dotenv for local development when secrets.toml is not
populated yet (i.e. SUPABASE_KEY is still the placeholder value).
"""
import os

import streamlit as st
from dotenv import load_dotenv
from supabase import Client, create_client


@st.cache_resource(show_spinner=False)
def get_client() -> Client:
    """Return a cached Supabase client.

    Priority:
    1. st.secrets (Streamlit Cloud / secrets.toml with real values)
    2. Environment variables from .env (local development)
    """
    url = st.secrets.get("SUPABASE_URL", "")
    key = st.secrets.get("SUPABASE_KEY", "")

    # Fall back to .env when secrets.toml placeholder is still in place
    if not url or not key or key == "REPLACE_WITH_ANON_KEY":
        load_dotenv()
        url = os.getenv("SUPABASE_URL", "")
        key = os.getenv("SUPABASE_KEY", "")

    if not url or not key:
        st.error(
            "Supabase credentials not found. "
            "Add SUPABASE_URL and SUPABASE_KEY to .streamlit/secrets.toml or .env"
        )
        st.stop()

    return create_client(url, key)
