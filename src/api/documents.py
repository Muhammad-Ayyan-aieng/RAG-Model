from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, status
from src.core.auth import get_user_role, require_admin
from src.core.limiter import validate_upload
from src.pipelines.ingestion import ingest_document
from src.database.vector_client import get_vector_client, get_collection_name
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
# Helper to get all points
# ================================
def get_all_points():
    client = get_vector_client()
    collection_name = get_collection_name()
    
    # Scroll through all points
    result = client.scroll(
        collection_name=collection_name,
        limit=10000,
        with_payload=True
    )
    return result[0]  # Returns list of points


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
    client = get_vector_client()
    collection_name = get_collection_name()
    
    # Search for existing document with same filename
    try:
        search_result = client.scroll(
            collection_name=collection_name,
            scroll_filter={
                "must": [{"key": "filename", "match": {"value": file.filename}}]
            },
            limit=1
        )
        if search_result[0]:
            logger.warning(f"Duplicate upload blocked: {file.filename}")
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Document '{file.filename}' already exists. Delete it first if you want to re-upload."
            )
    except Exception as e:
        # Collection might be empty, that's fine
        pass

    try:
        raw_text = await extract_text(file)
        clean = clean_text(raw_text)

        if not clean.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Document appears to be empty after processing"
            )

        # ================================
        # Check for duplicate content by hash
        # ================================
        content_hash = hashlib.md5(clean.encode()).hexdigest()
        
        try:
            hash_result = client.scroll(
                collection_name=collection_name,
                scroll_filter={
                    "must": [{"key": "content_hash", "match": {"value": content_hash}}]
                },
                limit=1
            )
            if hash_result[0]:
                existing_filename = hash_result[0][0].payload.get("filename", "unknown")
                logger.warning(f"Duplicate content blocked: {file.filename} (matches existing document: {existing_filename})")
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Document content already exists in document '{existing_filename}'. Delete that document first if you want to re-upload."
                )
        except Exception:
            pass

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
        points = get_all_points()
        
        if not points:
            return DocumentListResponse(total=0, documents=[])

        # Build document list from points
        documents_dict = {}
        for point in points:
            payload = point.payload
            doc_id = payload.get("document_id")
            
            if doc_id not in documents_dict:
                documents_dict[doc_id] = {
                    "document_id": doc_id,
                    "filename": payload.get("filename", "unknown"),
                    "chunks_count": 1,
                    "uploaded_at": payload.get("uploaded_at", "unknown")
                }
            else:
                documents_dict[doc_id]["chunks_count"] += 1
        
        documents = [DocumentInfo(**doc) for doc in documents_dict.values()]

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
        client = get_vector_client()
        collection_name = get_collection_name()
        
        # First, find all points with this document_id
        search_result = client.scroll(
            collection_name=collection_name,
            scroll_filter={
                "must": [{"key": "document_id", "match": {"value": document_id}}]
            },
            limit=10000,
            with_payload=True
        )
        
        points = search_result[0]
        if not points:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Document '{document_id}' not found"
            )
        
        # Delete each point
        point_ids = [point.id for point in points]
        client.delete(
            collection_name=collection_name,
            points_selector=point_ids
        )

        logger.info(
            f"Deleted document: {document_id} — "
            f"{len(points)} chunks removed"
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