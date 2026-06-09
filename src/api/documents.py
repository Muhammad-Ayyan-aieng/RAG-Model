from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, status, Header
from src.core.auth import get_user_role, require_admin
from src.core.limiter import validate_upload
from src.pipelines.ingestion import ingest_document
from src.database.vector_client import get_vector_client, get_collection_name
from src.utils.file_parser import extract_text
from src.config import settings
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
# Upload document (Authenticated - Private/Public)
# ================================
@router.post("/upload", response_model=DocumentUploadResponse)
async def upload_document(
    files: list[UploadFile] = File(...),
    x_admin_password: str = Header(None),
    current_user: dict = Depends(get_current_user),
    is_private: bool = False
):    
    # CHECK ADMIN FIRST - bypass everything
    if x_admin_password and x_admin_password == settings.ADMIN_PASSWORD:
        # Admin upload - no token needed
        user_id = "admin"
        user_role = "admin"
        logger.info(f"Admin upload: {files[0].filename}")
    else:
        # Normal user - use token
        user_id = current_user.get("user_id")
        user_role = current_user.get("role")
        logger.info(f"User upload: {files[0].filename} - {user_id}")

    # Validate upload limits (admin has no limits)
    if user_role != "admin":
        validate_upload(files, user_role)

    if len(files) > 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Upload one file at a time"
        )

    file = files[0]
    
    client = get_vector_client()
    collection_name = get_collection_name()
    
    # Check for duplicate filename (same user only)
    if user_role != "admin":
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
            logger.warning(f"Duplicate filename blocked: {file.filename}")
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"You already have a document named '{file.filename}'. Please delete it first or rename your file."
            )

    try:
        raw_text = await extract_text(file)
        clean = clean_text(raw_text)

        if not clean.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Document appears to be empty after processing"
            )

        content_hash = hashlib.md5(clean.encode()).hexdigest()
        
        # Check for duplicate content with privacy logic
        # First check if this content exists anywhere
        hash_result = client.scroll(
            collection_name=collection_name,
            scroll_filter={
                "must": [{"key": "content_hash", "match": {"value": content_hash}}]
            },
            limit=1
        )
        
        if hash_result[0]:
            existing_filename = hash_result[0][0].payload.get("filename", "unknown")
            existing_owner = hash_result[0][0].payload.get("user_id", "unknown")
            existing_is_private = hash_result[0][0].payload.get("is_private", False)
            
            # ADMIN: Can upload anything (no limits)
            if user_role == "admin":
                logger.info(f"Admin uploading duplicate content - allowed")
                # Continue with upload
            
            # SAME USER: Block duplicate
            elif existing_owner == user_id:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"You have already uploaded this content in '{existing_filename}'. Please delete it first."
                )
            
            # DIFFERENT USER: Check privacy of original
            elif existing_is_private == False:  # Original is PUBLIC
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"This content already exists as a PUBLIC document '{existing_filename}' (uploaded by another user). Duplicate public content is not allowed to save storage."
                )
            else:  # Original is PRIVATE - allow upload
                logger.info(f"Content exists but is private - allowing upload for different user")
                # Continue with upload

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
    
    # Check for duplicate filename
    search_result = client.scroll(
        collection_name=collection_name,
        scroll_filter={
            "must": [{"key": "filename", "match": {"value": file.filename}}]
        },
        limit=1
    )
    if search_result[0]:
        logger.warning(f"Duplicate filename blocked: {file.filename}")
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Document '{file.filename}' already exists."
        )
    
    try:
        raw_text = await extract_text(file)
        clean = clean_text(raw_text)
        
        if not clean.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Document appears to be empty after processing"
            )
        
        content_hash = hashlib.md5(clean.encode()).hexdigest()
        
        # Check for duplicate content (public uploads always block duplicates)
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
                detail=f"This content already exists in '{existing_filename}'. Duplicate not allowed."
            )
        
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
                    "uploaded_at": payload.get("uploaded_at", "unknown"),
                    "is_private": payload.get("is_private", False)
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
# ADMIN ONLY: Get all documents with user info
# ================================
@router.get("/admin/all")
async def admin_list_all_documents(
    x_admin_password: str = Header(...)
):
    """
    ADMIN ONLY: Get ALL documents with user information.
    Shows which user uploaded each document and privacy status.
    """
    # Verify admin password
    if x_admin_password != settings.ADMIN_PASSWORD:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid admin password"
        )
    
    logger.info("Admin fetching all documents with user info")
    
    try:
        points = get_all_points()
        
        if not points:
            return {
                "total": 0,
                "documents": []
            }
        
        # Group by document_id and collect all info
        documents_dict = {}
        for point in points:
            payload = point.payload
            if not payload:
                continue
                
            doc_id = payload.get("document_id")
            if not doc_id:
                continue
            
            if doc_id not in documents_dict:
                # Get user_id (could be None for public uploads)
                user_id = payload.get("user_id")
                is_private = payload.get("is_private", False)
                
                documents_dict[doc_id] = {
                    "document_id": doc_id,
                    "filename": payload.get("filename", "unknown"),
                    "chunks_count": 1,
                    "uploaded_at": payload.get("uploaded_at", "unknown"),
                    "user_id": user_id if user_id else "public",
                    "is_private": is_private,
                    "user_display": user_id[:8] + "..." if user_id and len(user_id) > 8 else (user_id if user_id else "Public User")
                }
            else:
                documents_dict[doc_id]["chunks_count"] += 1
        
        # Convert to list and sort by uploaded_at (newest first)
        documents = list(documents_dict.values())
        documents.sort(key=lambda x: x.get("uploaded_at", ""), reverse=True)
        
        logger.info(f"Admin fetched {len(documents)} documents")
        
        return {
            "total": len(documents),
            "documents": documents
        }
        
    except Exception as e:
        logger.error(f"Admin list documents failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve documents"
        )


# ================================
# ADMIN ONLY: Get user statistics
# ================================
@router.get("/admin/stats")
async def admin_get_stats(
    x_admin_password: str = Header(...)
):
    """
    ADMIN ONLY: Get system statistics including users, uploads, queries.
    """
    # Verify admin password
    if x_admin_password != settings.ADMIN_PASSWORD:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid admin password"
        )
    
    try:
        points = get_all_points()
        
        # Collect statistics
        unique_users = set()
        unique_documents = set()
        
        for point in points:
            payload = point.payload
            if not payload:
                continue
            
            user_id = payload.get("user_id")
            if user_id and user_id != "admin":
                unique_users.add(user_id)
            
            doc_id = payload.get("document_id")
            if doc_id:
                unique_documents.add(doc_id)
        
        return {
            "total_users": len(unique_users),
            "total_documents": len(unique_documents),
            "total_uploads": len(unique_documents),
            "total_queries": 0,
            "total_chunks": len(points)
        }
        
    except Exception as e:
        logger.error(f"Admin stats failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve statistics"
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


# ================================
# ADMIN ONLY: Delete any document by ID
# ================================
@router.delete("/admin/{document_id}")
async def admin_delete_document(
    document_id: str,
    x_admin_password: str = Header(...)
):
    """
    ADMIN ONLY: Delete any document by ID (bypasses ownership checks).
    """
    # Verify admin password
    if x_admin_password != settings.ADMIN_PASSWORD:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid admin password"
        )
    
    logger.info(f"Admin delete request — document_id: {document_id}")
    
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
        
        point_ids = [point.id for point in points]
        client.delete(
            collection_name=collection_name,
            points_selector=point_ids
        )
        
        logger.info(f"Admin deleted document: {document_id} — {len(points)} chunks removed")
        
        return {
            "message": "Document deleted successfully",
            "document_id": document_id,
            "chunks_deleted": len(points)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Admin delete failed for {document_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete document"
        )