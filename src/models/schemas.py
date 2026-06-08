from pydantic import BaseModel, field_validator
from typing import Optional
from datetime import datetime


# ================================
# Document schemas
# ================================
class DocumentUploadResponse(BaseModel):
    message: str
    filename: str
    chunks_created: int
    document_id: str


class DocumentInfo(BaseModel):
    document_id: str
    filename: str
    chunks_count: int
    uploaded_at: str


class DocumentListResponse(BaseModel):
    total: int
    documents: list[DocumentInfo]


class DocumentDeleteResponse(BaseModel):
    message: str
    document_id: str


# ================================
# Query schemas
# ================================
class QueryRequest(BaseModel):
    question: str
    top_k: Optional[int] = 3

    @field_validator("question")
    @classmethod
    def question_must_not_be_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Question cannot be empty")
        if len(v.strip()) < 3:
            raise ValueError("Question is too short")
        if len(v) > 1000:
            raise ValueError("Question is too long, maximum 1000 characters")
        return v.strip()

    @field_validator("top_k")
    @classmethod
    def top_k_must_be_valid(cls, v: Optional[int]) -> Optional[int]:
        if v is not None and (v < 1 or v > 10):
            raise ValueError("top_k must be between 1 and 10")
        return v


class SourceChunk(BaseModel):
    filename: str
    chunk_index: int
    text_preview: str


class QueryResponse(BaseModel):
    question: str
    answer: str
    sources: list[SourceChunk]
    model_used: str


# ================================
# Health schema
# ================================
class HealthResponse(BaseModel):
    status: str
    environment: str
    qdrant: str
    total_documents: int
    total_chunks: int