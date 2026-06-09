from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from src.utils.logger import setup_logging, get_logger

from src.config import settings
from src.api import documents, query, health
from src.api import auth_routes
from src.api import admin  # NEW: Import admin routes
from src.database.vector_client import init_vector_client
from src.database.supabase_client import init_supabase

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # ================================
    # Startup
    # ================================
    setup_logging()
    print(f"Starting RAG Assistant in {settings.APP_ENV} mode")

    # Initialize Vector Database (Qdrant) - with error handling
    try:
        init_vector_client()
        print("✅ Vector DB (Qdrant) initialized")
    except Exception as e:
        print(f"⚠️ Vector DB initialization failed: {e}")
        print("   App will continue but vector search may not work")

    # Initialize Supabase for user management - with error handling
    try:
        init_supabase()
        print("✅ Supabase initialized")
    except Exception as e:
        print(f"⚠️ Supabase initialization failed: {e}")
        print("   App will continue but user authentication may not work")

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
    allow_origins=[
        "https://rag-model-frontend.vercel.app",
        "http://localhost:3000",
        "http://localhost:5500",
        "http://127.0.0.1:5500",
        "http://localhost:8000",
    ],
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
app.include_router(admin.router)  # NEW: Admin routes (no prefix needed, already has /admin)
app.include_router(auth_routes.router)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "src.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )