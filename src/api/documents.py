from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, status
from src.core.auth import get_user_role, require_admin
from src.core.limiter import validate_upload
from src.pipelines.ingestion import ingest_document
from src.database.chroma_client import get_collection
from src.utils.file_parser import extract_text
from src.utils.text_cleaner import clean_text
from src.models.schemas import (
    DocumentUploadResponse,
    DocumentListResponse,
    DocumentDeleteResponse,
    DocumentInfo
)
from src.utils.logger import get_logger
import hashlib

logger = get_logger(__name__)

router = APIRouter()


# ================================
# Upload document
# ================================
@router.post("/upload", response_model=DocumentUploadResponse)
async def upload_document(
    files: list[UploadFile] = File(...),
    role: str = Depends(get_user_role)
):
    validate_upload(files, role)

    if len(files) > 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Upload one file at a time"
        )

    file = files[0]

    logger.info(f"Upload request — file: {file.filename} role: {role}")

    # ================================
    # Check for duplicate document by filename
    # ================================
    collection = get_collection()
    
    # Search for existing document with same filename
    existing = collection.get(
        where={"filename": file.filename},
        include=["metadatas"]
    )
    
    if existing["ids"]:
        logger.warning(f"Duplicate upload blocked: {file.filename}")
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Document '{file.filename}' already exists. Delete it first if you want to re-upload."
        )
    # ================================

    try:
        raw_text = await extract_text(file)
        clean = clean_text(raw_text)

        if not clean.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Document appears to be empty after processing"
            )

        # ================================
        # Check for duplicate content by hash (same content, different filename)
        # ================================
        content_hash = hashlib.md5(clean.encode()).hexdigest()
        
        existing_by_hash = collection.get(
            where={"content_hash": content_hash},
            include=["metadatas"]
        )
        
        if existing_by_hash["ids"]:
            existing_filename = existing_by_hash["metadatas"][0][0].get("filename", "unknown")
            logger.warning(f"Duplicate content blocked: {file.filename} (matches existing document: {existing_filename})")
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Document content already exists in document '{existing_filename}'. Delete that document first if you want to re-upload."
            )
        # ================================

        result = ingest_document(clean, file.filename, content_hash)

        logger.info(
            f"Upload complete — {file.filename} "
            f"chunks: {result['chunks_created']}"
        )

        return DocumentUploadResponse(
            message="Document uploaded successfully",
            filename=result["filename"],
            chunks_created=result["chunks_created"],
            document_id=result["document_id"]
        )

    except HTTPException:
        raise

    except ValueError as e:
        logger.warning(f"Upload validation error: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

    except Exception as e:
        logger.error(f"Upload failed for {file.filename}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process document. Please try again."
        )


# ================================
# List all documents
# ================================
@router.get("/", response_model=DocumentListResponse)
async def list_documents(
    role: str = Depends(get_user_role)
):
    require_admin(role)
    logger.debug(f"List documents requested — role: {role}")

    try:
        collection = get_collection()

        if collection.count() == 0:
            return DocumentListResponse(total=0, documents=[])

        results = collection.get(include=["metadatas"])

        documents = _build_document_list(results["metadatas"])

        return DocumentListResponse(
            total=len(documents),
            documents=documents
        )

    except Exception as e:
        logger.error(f"Failed to list documents: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve document list"
        )


# ================================
# Delete document
# ================================
@router.delete("/{document_id}", response_model=DocumentDeleteResponse)
async def delete_document(
    document_id: str,
    role: str = Depends(get_user_role)
):
    require_admin(role)

    logger.info(f"Delete request — document_id: {document_id} role: {role}")

    try:
        collection = get_collection()

        existing = collection.get(
            where={"document_id": document_id},
            include=["metadatas"]
        )

        if not existing["ids"]:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Document '{document_id}' not found"
            )

        collection.delete(
            where={"document_id": document_id}
        )

        logger.info(
            f"Deleted document: {document_id} — "
            f"{len(existing['ids'])} chunks removed"
        )

        return DocumentDeleteResponse(
            message="Document deleted successfully",
            document_id=document_id
        )

    except HTTPException:
        raise

    except Exception as e:
        logger.error(f"Delete failed for {document_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete document"
        )


# ================================
# Internal helpers
# ================================
def _build_document_list(metadatas: list[dict]) -> list[DocumentInfo]:
    seen = {}

    for metadata in metadatas:
        doc_id = metadata.get("document_id")

        if not doc_id:
            continue

        if doc_id not in seen:
            seen[doc_id] = DocumentInfo(
                document_id=doc_id,
                filename=metadata.get("filename", "unknown"),
                chunks_count=1,
                uploaded_at=metadata.get("uploaded_at", "unknown")
            )
        else:
            seen[doc_id].chunks_count += 1

    return list(seen.values())