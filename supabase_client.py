from supabase import create_client, Client
from config import settings

def get_supabase_client() -> Client:
    """Get Supabase client with service role key for admin operations"""
    return create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_ROLE_KEY)

def get_supabase_anon_client() -> Client:
    """Get Supabase client with anonymous key for public operations"""
    return create_client(settings.SUPABASE_URL, settings.SUPABASE_ANON_KEY)

# Initialize clients
supabase_admin = get_supabase_client()
supabase_anon = get_supabase_anon_client()