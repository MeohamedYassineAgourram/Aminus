import os
from typing import Optional


def get_supabase_client() -> Optional[object]:
    """
    Returns a Supabase client if configured, otherwise None.
    Uses the service role key so the backend can write to DB + Storage.
    """

    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    if not url or not key:
        return None

    from supabase import create_client  # lazy import

    return create_client(url, key)

