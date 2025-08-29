from supabase import create_client, Client
from config import settings
from functools import lru_cache

@lru_cache(maxsize=1)
def get_supabase_client() -> Client:
    """Get Supabase client with service role key for admin operations"""
    try:
        return create_client(
            settings.SUPABASE_URL, 
            settings.SUPABASE_SERVICE_ROLE_KEY,
            options={
                "schema": "public",
                "auto_refresh_token": True,
                "persist_session": True
            }
        )
    except Exception as e:
        print(f"Error creating Supabase admin client: {e}")
        raise

@lru_cache(maxsize=1)
def get_supabase_anon_client() -> Client:
    """Get Supabase client with anonymous key for public operations"""
    try:
        return create_client(
            settings.SUPABASE_URL, 
            settings.SUPABASE_ANON_KEY,
            options={
                "schema": "public",
                "auto_refresh_token": True,
                "persist_session": True
            }
        )
    except Exception as e:
        print(f"Error creating Supabase anon client: {e}")
        raise

# Lazy initialization functions to avoid module-level initialization
def get_supabase_admin():
    """Get cached Supabase admin client"""
    return get_supabase_client()

def get_supabase_anon():
    """Get cached Supabase anonymous client"""
    return get_supabase_anon_client()
