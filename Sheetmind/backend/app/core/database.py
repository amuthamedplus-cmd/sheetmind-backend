from supabase import create_client, Client

from app.core.config import settings

# Service role client — bypasses RLS, used for backend operations
_supabase_client: Client | None = None

# Anon-key client — used for auth operations (token validation, sign-up, sign-in)
_anon_client: Client | None = None


def get_supabase() -> Client:
    """Get the Supabase client (service role). Lazily initialized."""
    global _supabase_client
    if _supabase_client is None:
        _supabase_client = create_client(
            settings.SUPABASE_URL,
            settings.SUPABASE_SERVICE_ROLE_KEY,
        )
    return _supabase_client


def get_supabase_anon() -> Client:
    """Get the Supabase client (anon key, for auth). Lazily initialized.

    Shared singleton to avoid creating a new HTTP pool on every request.
    """
    global _anon_client
    if _anon_client is None:
        _anon_client = create_client(
            settings.SUPABASE_URL,
            settings.SUPABASE_ANON_KEY,
        )
    return _anon_client
