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
from src.auth.auth import get_current_user, is_admin
import hashlib

logger = get_logger(__name__)

router = APIRouter()


# ================================
# Helper to get all points (Admin only)
# ================================
def get_all_points():
    client = get_vector_client()
    collection_name = get_collection_name()
    
    result = client.scroll(
        collection_name=collection_name,
        limit=10000,
        with_payload=True
    )
    return result[0]


# ================================
# Helper to get user's documents only
# ================================
def get_user_documents(user_id: str):
    client = get_vector_client()
    collection_name = get_collection_name()
    
    result = client.scroll(
        collection_name=collection_name,
        limit=10000,
        with_payload=True
    )
    points = result[0]
    
    user_points = [p for p in points if p.payload and p.payload.get("user_id") == user_id]
    
    return user_points


# ================================
# Upload document (Authenticated - Private)
# ================================
@router.post("/upload", response_model=DocumentUploadResponse)
async def upload_document(
    files: list[UploadFile] = File(...),
    current_user: dict = Depends(get_current_user),
    is_private: bool = False
):
    """
    Upload a document. Authenticated users only.
    
    - is_private: If True, only you and admin can see this document
    """
    validate_upload(files, current_user.get("role"))

    if len(files) > 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Upload one file at a time"
        )

    file = files[0]
    user_id = current_user.get("user_id")
    user_role = current_user.get("role")

    logger.info(f"Upload request — file: {file.filename} user: {user_id} role: {user_role}")

    client = get_vector_client()
    collection_name = get_collection_name()
    
    try:
        search_result = client.scroll(
            collection_name=collection_name,
            scroll_filter={
                "must": [
                    {"key": "filename", "match": {"value": file.filename}},
                    {"key": "user_id", "match": {"value": user_id}}
                ]
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
        pass

    try:
        raw_text = await extract_text(file)
        clean = clean_text(raw_text)

        if not clean.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Document appears to be empty after processing"
            )

        content_hash = hashlib.md5(clean.encode()).hexdigest()
        
        try:
            hash_result = client.scroll(
                collection_name=collection_name,
                scroll_filter={
                    "must": [
                        {"key": "content_hash", "match": {"value": content_hash}},
                        {"key": "user_id", "match": {"value": user_id}}
                    ]
                },
                limit=1
            )
            if hash_result[0]:
                existing_filename = hash_result[0][0].payload.get("filename", "unknown")
                logger.warning(f"Duplicate content blocked: {file.filename}")
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Document content already exists in '{existing_filename}'"
                )
        except Exception:
            pass

        result = ingest_document(
            text=clean, 
            filename=file.filename, 
            content_hash=content_hash,
            user_id=user_id,
            is_private=is_private
        )

        logger.info(f"Upload complete — {file.filename} chunks: {result['chunks_created']}")

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
# Upload document (Public - No Auth)
# ================================
@router.post("/upload/public", response_model=DocumentUploadResponse)
async def upload_document_public(
    files: list[UploadFile] = File(...),
):
    """
    Upload a document WITHOUT authentication.
    Documents become public (no user ownership, everyone can see).
    """
    validate_upload(files, "public")
    
    if len(files) > 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Upload one file at a time"
        )
    
    file = files[0]
    logger.info(f"Public upload request — file: {file.filename}")
    
    client = get_vector_client()
    collection_name = get_collection_name()
    
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
                detail=f"Document '{file.filename}' already exists."
            )
    except Exception as e:
        pass
    
    try:
        raw_text = await extract_text(file)
        clean = clean_text(raw_text)
        
        if not clean.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Document appears to be empty after processing"
            )
        
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
                logger.warning(f"Duplicate content blocked: {file.filename}")
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Document content already exists in '{existing_filename}'"
                )
        except Exception:
            pass
        
        result = ingest_document(
            text=clean, 
            filename=file.filename, 
            content_hash=content_hash,
            user_id=None,
            is_private=False
        )
        
        logger.info(f"Public upload complete — {file.filename} chunks: {result['chunks_created']}")
        
        return DocumentUploadResponse(
            message="Public document uploaded successfully",
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
        logger.error(f"Public upload failed for {file.filename}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process document. Please try again."
        )


# ================================
# List documents (User sees own, Admin sees all)
# ================================
@router.get("/", response_model=DocumentListResponse)
async def list_documents(
    current_user: dict = Depends(get_current_user)
):
    user_id = current_user.get("user_id")
    user_role = current_user.get("role")
    
    logger.debug(f"List documents requested — user: {user_id} role: {user_role}")

    try:
        if user_role == "admin":
            points = get_all_points()
        else:
            points = get_user_documents(user_id)
        
        if not points:
            return DocumentListResponse(total=0, documents=[])

        documents_dict = {}
        for point in points:
            payload = point.payload
            if not payload:
                continue
                
            doc_id = payload.get("document_id")
            if not doc_id:
                continue
            
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
# Delete document (Owner or Admin)
# ================================
@router.delete("/{document_id}", response_model=DocumentDeleteResponse)
async def delete_document(
    document_id: str,
    current_user: dict = Depends(get_current_user)
):
    user_id = current_user.get("user_id")
    user_role = current_user.get("role")

    logger.info(f"Delete request — document_id: {document_id} user: {user_id} role: {user_role}")

    try:
        client = get_vector_client()
        collection_name = get_collection_name()
        
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
        
        doc_owner_id = points[0].payload.get("user_id")
        
        if user_role != "admin" and doc_owner_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only delete your own documents"
            )
        
        point_ids = [point.id for point in points]
        client.delete(
            collection_name=collection_name,
            points_selector=point_ids
        )

        logger.info(f"Deleted document: {document_id} — {len(points)} chunks removed")

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