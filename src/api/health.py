from fastapi import APIRouter
from src.database.vector_client import get_vector_client, get_collection_name
from src.models.schemas import HealthResponse
from src.config import settings
from src.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter()


# ================================
# Health check endpoint
# ================================
@router.get("/health", response_model=HealthResponse)
async def health_check():
    logger.debug("Health check requested")

    qdrant_status, total_documents, total_chunks = _check_qdrant()

    return HealthResponse(
        status="healthy",
        environment=settings.APP_ENV,
        qdrant=qdrant_status, 
        total_documents=total_documents,
        total_chunks=total_chunks
    )


# ================================
# Internal helpers
# ================================
def _check_qdrant() -> tuple[str, int, int]:
    try:
        client = get_vector_client()
        collection_name = get_collection_name()
        
        # Get collection info
        collection_info = client.get_collection(collection_name)
        total_chunks = collection_info.points_count
        
        # Get unique document IDs from payloads
        result = client.scroll(
            collection_name=collection_name,
            limit=10000,
            with_payload=True
        )
        points = result[0]
        
        unique_docs = set()
        for point in points:
            if point.payload and "document_id" in point.payload:
                unique_docs.add(point.payload["document_id"])
        
        total_documents = len(unique_docs)
        
        return "connected", total_documents, total_chunks

    except Exception as e:
        logger.error(f"Qdrant health check failed: {e}")
        return "disconnected", 0, 0