from supabase import create_client, Client

from app.core.config import settings

# Service role client — bypasses RLS, used for backend operations
_supabase_client: Client | None = None


def get_supabase() -> Client:
    """Get the Supabase client (service role). Lazily initialized."""
    global _supabase_client
    if _supabase_client is None:
        _supabase_client = create_client(
            settings.SUPABASE_URL,
            settings.SUPABASE_SERVICE_ROLE_KEY,
        )
    return _supabase_client
