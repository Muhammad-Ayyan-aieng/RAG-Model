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

    chromadb_status, total_chunks, total_documents = _check_chromadb()

    return HealthResponse(
        status="healthy",
        environment=settings.APP_ENV,
        chromadb=chromadb_status,
        total_documents=total_documents,
        total_chunks=total_chunks
    )


# ================================
# Internal helpers
# ================================
def _check_chromadb() -> tuple[str, int, int]:
    try:
        collection = get_collection()
        total_chunks = collection.count()
        total_documents = _count_unique_documents(collection)
        return "connected", total_chunks, total_documents

    except Exception as e:
        logger.error(f"ChromaDB health check failed: {e}")
        return "disconnected", 0, 0


def _count_unique_documents(collection) -> int:
    try:
        if collection.count() == 0:
            return 0

        results = collection.get(include=["metadatas"])

        if not results["metadatas"]:
            return 0

        unique_ids = set(
            metadata["document_id"]
            for metadata in results["metadatas"]
            if "document_id" in metadata
        )

        return len(unique_ids)

    except Exception as e:
        logger.error(f"Failed to count unique documents: {e}")
        return 0