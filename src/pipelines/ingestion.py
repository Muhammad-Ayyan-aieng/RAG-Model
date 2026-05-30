import uuid
import hashlib
from datetime import datetime
from fast_sentence_transformers import FastSentenceTransformer as SentenceTransformer 
from src.config import settings
from src.utils.logger import get_logger
from src.database.chroma_client import get_collection

logger = get_logger(__name__)

# ================================
# Single embedding model instance
# ================================
_embedding_model = None

CHUNK_SIZE = 500
CHUNK_OVERLAP = 100


def get_embedding_model():
    global _embedding_model

    if _embedding_model is None:
        logger.info("Loading embedding model — this takes a moment on first run")
        _embedding_model = SentenceTransformer("all-MiniLM-L6-v2", quantize=True)
        logger.info("Embedding model loaded successfully (quantized mode - lower memory)")

    return _embedding_model


# ================================
# Main entry point
# ================================
def ingest_document(text: str, filename: str, content_hash: str = None) -> dict:
    logger.info(f"Starting ingestion: {filename}")

    # Generate hash if not provided
    if content_hash is None:
        content_hash = hashlib.md5(text.encode()).hexdigest()

    document_id = _generate_document_id()
    uploaded_at = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")

    chunks = _split_into_chunks(text)
    logger.info(f"Split into {len(chunks)} chunks")

    embeddings = _create_embeddings(chunks)
    logger.debug("Embeddings created")

    _store_in_chromadb(
        chunks=chunks,
        embeddings=embeddings,
        document_id=document_id,
        filename=filename,
        uploaded_at=uploaded_at,
        content_hash=content_hash
    )

    logger.info(
        f"Ingestion complete: {filename} — "
        f"{len(chunks)} chunks stored with id: {document_id}"
    )

    return {
        "document_id": document_id,
        "filename": filename,
        "chunks_created": len(chunks),
        "uploaded_at": uploaded_at
    }


# ================================
# Internal helpers
# ================================
def _generate_document_id() -> str:
    return str(uuid.uuid4())


def _split_into_chunks(text: str) -> list[str]:
    chunks = []
    start = 0
    text_length = len(text)

    while start < text_length:
        end = start + CHUNK_SIZE

        # dont cut in middle of word
        if end < text_length:
            while end > start and text[end] not in " \n":
                end -= 1
            if end == start:
                end = start + CHUNK_SIZE

        chunk = text[start:end].strip()

        if chunk:
            chunks.append(chunk)

        start = end - CHUNK_OVERLAP

        if start >= text_length:
            break

    return chunks


def _create_embeddings(chunks: list[str]) -> list[list[float]]:
    model = get_embedding_model()
    embeddings = model.encode(chunks, show_progress_bar=False)
    return embeddings.tolist()


def _store_in_chromadb(
    chunks: list[str],
    embeddings: list[list[float]],
    document_id: str,
    filename: str,
    uploaded_at: str,
    content_hash: str = None
) -> None:
    collection = get_collection()

    ids = [
        f"{document_id}_chunk_{i}"
        for i in range(len(chunks))
    ]

    metadatas = [
        {
            "document_id": document_id,
            "filename": filename,
            "chunk_index": i,
            "uploaded_at": uploaded_at,
            "content_hash": content_hash
        }
        for i in range(len(chunks))
    ]

    collection.add(
        ids=ids,
        embeddings=embeddings,
        documents=chunks,
        metadatas=metadatas
    )

    logger.debug(f"Stored {len(chunks)} chunks in ChromaDB")