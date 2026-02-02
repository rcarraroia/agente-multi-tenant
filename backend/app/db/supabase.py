from supabase import create_client, Client
from app.config import settings
from typing import Optional

class SupabaseClient:
    _instance: Optional[Client] = None

    @classmethod
    def get_client(cls) -> Client:
        if cls._instance is None:
            if not settings.SUPABASE_URL or not settings.SUPABASE_SERVICE_KEY:
                raise ValueError("SUPABASE_URL and SUPABASE_SERVICE_KEY must be set")
            
            cls._instance = create_client(
                settings.SUPABASE_URL,
                settings.SUPABASE_SERVICE_KEY
            )
        return cls._instance

def get_supabase() -> Client:
    """Dependency to get Supabase client"""
    return SupabaseClient.get_client()

# Placeholder for future tenant-aware helpers
class TenantSupabase:
    def __init__(self, tenant_id: str):
        self.client = get_supabase()
        self.tenant_id = tenant_id

    # Add methods to interact with DB filtering by tenant_id automatically
