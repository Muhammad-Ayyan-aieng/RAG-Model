from src.database.chroma_client import get_collection
from src.pipelines.ingestion import get_embedding_model
from src.models.llm_factory import generate_answer
from src.models.schemas import SourceChunk
from src.utils.logger import get_logger

logger = get_logger(__name__)


# ================================
# Main entry point
# ================================
def retrieve_and_answer(question: str, top_k: int = 3) -> dict:
    logger.info(f"Processing question: '{question}'")

    chunks, metadatas = _search_chromadb(question, top_k)

    if not chunks:
        logger.warning("No relevant chunks found in ChromaDB")
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


# ================================
# Internal helpers
# ================================
def _search_chromadb(question: str, top_k: int) -> tuple[list[str], list[dict]]:
    collection = get_collection()

    model = get_embedding_model()
    question_embedding = model.encode([question]).tolist()[0]

    logger.debug(f"Searching ChromaDB — top_k: {top_k}")

    results = collection.query(
        query_embeddings=[question_embedding],
        n_results=min(top_k, collection.count()) if collection.count() > 0 else 1,
        include=["documents", "metadatas", "distances"]
    )

    if not results["documents"] or not results["documents"][0]:
        return [], []

    chunks = results["documents"][0]
    metadatas = results["metadatas"][0]
    distances = results["distances"][0]

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