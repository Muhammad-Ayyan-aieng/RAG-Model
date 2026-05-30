import chromadb
from chromadb.config import Settings as ChromaSettings
from src.config import settings

# ================================
# Single ChromaDB client instance
# ================================
_client = None
_collection = None


def init_chroma() -> None:
    global _client, _collection

    _client = chromadb.PersistentClient(
        path=settings.CHROMA_PATH,
        settings=ChromaSettings(
            anonymized_telemetry=False
        )
    )

    _collection = _client.get_or_create_collection(
        name=settings.CHROMA_COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"}
    )

    print(f"ChromaDB ready — collection: '{settings.CHROMA_COLLECTION_NAME}'")
    print(f"Documents in DB: {_collection.count()}")


def get_collection():
    if _collection is None:
        raise RuntimeError("ChromaDB not initialized. init_chroma() was not called on startup.")
    return _collection


def get_client():
    if _client is None:
        raise RuntimeError("ChromaDB not initialized. init_chroma() was not called on startup.")
    return _client