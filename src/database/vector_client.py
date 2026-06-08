from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams
from src.config import settings
from src.utils.logger import get_logger

logger = get_logger(__name__)

# ================================
# Single Qdrant client instance
# ================================
_client = None
_collection_name = settings.QDRANT_COLLECTION_NAME


def init_vector_client() -> None:
    global _client
    
    logger.info(f"Connecting to Qdrant Cloud at: {settings.QDRANT_URL}")
    
    _client = QdrantClient(
        url=settings.QDRANT_URL,
        api_key=settings.QDRANT_API_KEY,
        timeout=30.0,
    )
    
    # Create collection if it doesn't exist
    try:
        _client.create_collection(
            collection_name=_collection_name,
            vectors_config=VectorParams(
                size=settings.QDRANT_VECTOR_SIZE,
                distance=Distance.COSINE
            )
        )
        logger.info(f"Collection '{_collection_name}' created")
    except Exception as e:
        logger.info(f"Collection '{_collection_name}' already exists: {e}")
    
    # Create index on document_id for fast deletion
    try:
        _client.create_payload_index(
            collection_name=_collection_name,
            field_name="document_id",
            field_type="keyword"
        )
        logger.info("Created index on 'document_id'")
        
    except Exception as e:
        logger.info(f"Index on 'document_id' may already exist: {e}")

    # NEW: Create index on user_id for filtering
    try:
        _client.create_payload_index(
            collection_name=_collection_name,
            field_name="user_id",
            field_type="keyword"
        )
        logger.info("Created index on 'user_id'")
        
    except Exception as e:
        logger.info(f"Index on 'user_id' may already exist: {e}")

    # NEW: Create index on is_private for filtering
    try:
        _client.create_payload_index(
            collection_name=_collection_name,
            field_name="is_private",
            field_type="bool"
        )
        logger.info("Created index on 'is_private'")
        
    except Exception as e:
        logger.info(f"Index on 'is_private' may already exist: {e}")
    
    # Get collection info
    try:
        collection_info = _client.get_collection(_collection_name)
        logger.info(f"Qdrant ready — collection: '{_collection_name}'")
        logger.info(f"Points in DB: {collection_info.points_count}")
        logger.info(f"Points in DB: {collection_info.points_count}")
    except Exception as e:
        logger.warning(f"Could not get collection info: {e}")


def get_vector_client():
    if _client is None:
        raise RuntimeError("Qdrant not initialized. init_vector_client() was not called on startup.")
    return _client


def get_collection_name() -> str:
    return _collection_name