from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from src.utils.logger import setup_logging, get_logger

from src.config import settings
from src.api import documents, query, health
from src.database.chroma_client import init_chroma

logger = get_logger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # ================================
    # Startup
    # ================================
    setup_logging() 
    print(f"Starting RAG Assistant in {settings.APP_ENV} mode")
    init_chroma()
    print("ChromaDB initialized")
    yield
    # ================================
    # Shutdown
    # ================================
    print("Shutting down RAG Assistant")


app = FastAPI(
    title="RAG Document Assistant",
    description="Upload documents and ask questions grounded in your data",
    version="1.0.0",
    lifespan=lifespan
)


# ================================
# Middleware
# ================================
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if not settings.is_production() else ["https://yourdomain.com"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ================================
# Routers
# ================================
app.include_router(health.router, tags=["Health"])
app.include_router(documents.router, prefix="/documents", tags=["Documents"])
app.include_router(query.router, prefix="/query", tags=["Query"])


# ================================
# Serve Frontend
# ================================
app.mount("/", StaticFiles(directory="frontend", html=True), name="frontend")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "src.main:app",
        host="127.0.0.1",
        port=8000,
        reload=True
    )