from supabase import create_client, Client
from src.config import settings
from src.utils.logger import get_logger

logger = get_logger(__name__)

_supabase_client: Client = None


def init_supabase() -> None:
    """Initialize Supabase client on startup."""
    global _supabase_client
    
    logger.info("Connecting to Supabase...")
    
    _supabase_client = create_client(
        supabase_url=settings.SUPABASE_URL,
        supabase_key=settings.SUPABASE_ANON_KEY
    )
    
    logger.info("Supabase client initialized successfully")


def get_supabase_client() -> Client:
    """Get Supabase client instance."""
    if _supabase_client is None:
        raise RuntimeError("Supabase not initialized. Call init_supabase() first.")
    return _supabase_client