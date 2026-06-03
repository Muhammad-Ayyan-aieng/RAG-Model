from src.database.vector_client import get_vector_client, get_collection_name
from src.pipelines.ingestion import get_embedding_model
from src.models.llm_factory import generate_answer
from src.models.schemas import SourceChunk
from src.utils.logger import get_logger

logger = get_logger(__name__)


def retrieve_and_answer(question: str, top_k: int = 3) -> dict:
    logger.info(f"Processing question: '{question}'")

    chunks, metadatas = _search_qdrant(question, top_k)

    if not chunks:
        logger.warning("No relevant chunks found in Qdrant")
        return {
            "question": question,
            "answer": "I could not find relevant information in the uploaded documents.",
            "sources": [],
            "model_used": "none"
        }

    answer = generate_answer(question, chunks)
    sources = _build_sources(chunks, metadatas)

    logger.info(f"Answer ready — {len(sources)} sources used")

    return {
        "question": question,
        "answer": answer,
        "sources": sources,
        "model_used": "none"
    }


def _search_qdrant(question: str, top_k: int) -> tuple[list[str], list[dict]]:
    client = get_vector_client()
    collection_name = get_collection_name()
    
    model = get_embedding_model()
    question_embedding = model.encode([question]).tolist()[0]
    
    logger.debug(f"Searching Qdrant — top_k: {top_k}")
    
    try:
        collection_info = client.get_collection(collection_name)
        if collection_info.points_count == 0:
            logger.warning("Qdrant collection is empty")
            return [], []
    except Exception as e:
        logger.error(f"Error accessing Qdrant collection: {e}")
        return [], []
    
    # Correct: query_points with "query" parameter
    result = client.query_points(
        collection_name=collection_name,
        query=question_embedding,
        limit=top_k,
        with_payload=True
    )
    
    if not result or not hasattr(result, 'points'):
        return [], []
    
    results_list = result.points
    
    if not results_list:
        return [], []
    
    chunks = [r.payload.get("text", "") for r in results_list]
    metadatas = [{
        "document_id": r.payload.get("document_id"),
        "filename": r.payload.get("filename"),
        "chunk_index": r.payload.get("chunk_index")
    } for r in results_list]
    distances = [1 - r.score for r in results_list]
    
    chunks, metadatas = _filter_by_relevance(chunks, metadatas, distances)
    
    return chunks, metadatas


def _filter_by_relevance(
    chunks: list[str],
    metadatas: list[dict],
    distances: list[float],
    threshold: float = 0.7
) -> tuple[list[str], list[dict]]:

    filtered_chunks = []
    filtered_metadatas = []

    for chunk, metadata, distance in zip(chunks, metadatas, distances):
        if distance <= threshold:
            filtered_chunks.append(chunk)
            filtered_metadatas.append(metadata)
            logger.debug(f"Chunk accepted — distance: {distance:.3f}")
        else:
            logger.debug(f"Chunk rejected — distance: {distance:.3f} exceeds threshold")

    return filtered_chunks, filtered_metadatas


def _build_sources(
    chunks: list[str],
    metadatas: list[dict]
) -> list[SourceChunk]:

    sources = []

    for chunk, metadata in zip(chunks, metadatas):
        preview = chunk[:200] + "..." if len(chunk) > 200 else chunk

        source = SourceChunk(
            filename=metadata.get("filename", "unknown"),
            chunk_index=metadata.get("chunk_index", 0),
            text_preview=preview
        )
        sources.append(source)

    return sources