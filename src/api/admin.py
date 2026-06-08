from fastapi import APIRouter, Depends, HTTPException, status
from src.database.supabase_client import get_supabase_client
from src.database.vector_client import get_vector_client, get_collection_name
from src.auth.auth import get_current_user, is_admin
from src.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/admin", tags=["Admin"])


# ================================
# Get system statistics
# ================================
@router.get("/stats")
async def get_system_stats(current_user: dict = Depends(is_admin)):
    """
    Get system-wide statistics (Admin only).
    
    Returns:
        - total_users: Number of registered users
        - total_documents: Number of unique documents
        - total_chunks: Number of vector chunks
        - total_queries: Total queries made (if tracked)
        - total_uploads: Total uploads made
    """
    try:
        # Get user stats from Supabase
        supabase = get_supabase_client()
        
        # Get total users count
        users_result = supabase.table("users").select("id", count="exact").execute()
        total_users = users_result.count if hasattr(users_result, 'count') else 0
        
        # If count doesn't work, get all and count
        if total_users == 0:
            all_users = supabase.table("users").select("id").execute()
            total_users = len(all_users.data) if all_users.data else 0
        
        # Get document stats from Qdrant
        client = get_vector_client()
        collection_name = get_collection_name()
        
        collection_info = client.get_collection(collection_name)
        total_chunks = collection_info.points_count
        
        # Get unique document count from payloads
        result = client.scroll(
            collection_name=collection_name,
            limit=10000,
            with_payload=True
        )
        points = result[0]
        
        unique_docs = set()
        for point in points:
            if point.payload and "document_id" in point.payload:
                unique_docs.add(point.payload["document_id"])
        
        total_documents = len(unique_docs)
        
        # Get total uploads and queries from users table (sum of all users)
        users_data = supabase.table("users").select("total_uploads, total_queries").execute()
        
        total_uploads = 0
        total_queries = 0
        if users_data.data:
            for user in users_data.data:
                total_uploads += user.get("total_uploads", 0)
                total_queries += user.get("total_queries", 0)
        
        return {
            "status": "success",
            "data": {
                "total_users": total_users,
                "total_documents": total_documents,
                "total_chunks": total_chunks,
                "total_uploads": total_uploads,
                "total_queries": total_queries
            }
        }
        
    except Exception as e:
        logger.error(f"Failed to get system stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve statistics: {str(e)}"
        )


# ================================
# Get all users (Admin only)
# ================================
@router.get("/users")
async def get_all_users(
    limit: int = 100,
    offset: int = 0,
    current_user: dict = Depends(is_admin)
):
    """
    Get list of all registered users (Admin only).
    
    Args:
        limit: Number of users to return (default 100)
        offset: Pagination offset (default 0)
    
    Returns:
        List of users with their stats
    """
    try:
        supabase = get_supabase_client()
        
        # Get users with pagination
        result = supabase.table("users").select(
            "id, email, role, created_at, name, total_uploads, total_queries"
        ).range(offset, offset + limit - 1).order("created_at", desc=True).execute()
        
        # Get total count
        count_result = supabase.table("users").select("id", count="exact").execute()
        total = count_result.count if hasattr(count_result, 'count') else 0
        
        if total == 0 and result.data:
            total = len(result.data)
        
        return {
            "status": "success",
            "data": {
                "total": total,
                "limit": limit,
                "offset": offset,
                "users": result.data if result.data else []
            }
        }
        
    except Exception as e:
        logger.error(f"Failed to get users list: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve users: {str(e)}"
        )


# ================================
# Get user by ID (Admin only)
# ================================
@router.get("/users/{user_id}")
async def get_user_by_id_admin(
    user_id: str,
    current_user: dict = Depends(is_admin)
):
    """
    Get detailed information about a specific user (Admin only).
    
    Returns user details and their document stats.
    """
    try:
        supabase = get_supabase_client()
        
        # Get user details
        result = supabase.table("users").select(
            "id, email, role, created_at, name, total_uploads, total_queries"
        ).eq("id", user_id).execute()
        
        if not result.data or len(result.data) == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User with ID '{user_id}' not found"
            )
        
        user = result.data[0]
        
        # Get user's document stats from Qdrant
        client = get_vector_client()
        collection_name = get_collection_name()
        
        # Find all chunks belonging to this user
        scroll_result = client.scroll(
            collection_name=collection_name,
            scroll_filter={
                "must": [{"key": "user_id", "match": {"value": user_id}}]
            },
            limit=10000,
            with_payload=True
        )
        
        points = scroll_result[0]
        
        # Count unique documents for this user
        user_docs = set()
        for point in points:
            if point.payload and "document_id" in point.payload:
                user_docs.add(point.payload["document_id"])
        
        user["documents_count"] = len(user_docs)
        user["chunks_count"] = len(points)
        
        return {
            "status": "success",
            "data": user
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get user details: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve user: {str(e)}"
        )


# ================================
# Get all documents (Admin only)
# ================================
@router.get("/documents")
async def get_all_documents_admin(
    limit: int = 100,
    offset: int = 0,
    current_user: dict = Depends(is_admin)
):
    """
    Get all documents in the system with owner info (Admin only).
    
    Returns list of all documents with their owners.
    """
    try:
        client = get_vector_client()
        collection_name = get_collection_name()
        
        # Scroll through all points
        result = client.scroll(
            collection_name=collection_name,
            limit=limit + offset,
            with_payload=True
        )
        
        points = result[0]
        
        # Build unique documents list
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
                    "user_id": payload.get("user_id", "public"),
                    "uploaded_at": payload.get("uploaded_at", "unknown"),
                    "is_private": payload.get("is_private", False),
                    "chunks_count": 1
                }
            else:
                documents_dict[doc_id]["chunks_count"] += 1
        
        # Convert to list and paginate
        all_documents = list(documents_dict.values())
        
        # Sort by uploaded_at (newest first)
        all_documents.sort(key=lambda x: x.get("uploaded_at", ""), reverse=True)
        
        # Apply pagination
        paginated_docs = all_documents[offset:offset + limit]
        
        # Get usernames for user_ids
        supabase = get_supabase_client()
        unique_user_ids = set(doc.get("user_id") for doc in paginated_docs if doc.get("user_id") and doc.get("user_id") != "public")
        
        user_names = {}
        for user_id in unique_user_ids:
            if user_id:
                user_result = supabase.table("users").select("email, name").eq("id", user_id).execute()
                if user_result.data:
                    user_names[user_id] = user_result.data[0].get("name") or user_result.data[0].get("email")
        
        # Add owner name to documents
        for doc in paginated_docs:
            doc["owner_name"] = user_names.get(doc.get("user_id"), "Public" if doc.get("user_id") == "public" else "Unknown")
        
        return {
            "status": "success",
            "data": {
                "total": len(all_documents),
                "limit": limit,
                "offset": offset,
                "documents": paginated_docs
            }
        }
        
    except Exception as e:
        logger.error(f"Failed to get documents: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve documents: {str(e)}"
        )


# ================================
# Update user role (Admin only)
# ================================
@router.put("/users/{user_id}/role")
async def update_user_role_admin(
    user_id: str,
    role: str,
    current_user: dict = Depends(is_admin)
):
    """
    Update a user's role (Admin only).
    
    Args:
        user_id: User's UUID
        role: New role ("user" or "admin")
    """
    from src.database.user_db import update_user_role as db_update_role
    
    if role not in ["user", "admin"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Role must be 'user' or 'admin'"
        )
    
    try:
        updated_user = db_update_role(user_id, role)
        
        return {
            "status": "success",
            "message": f"User role updated to '{role}'",
            "data": updated_user
        }
        
    except Exception as e:
        logger.error(f"Failed to update user role: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


# ================================
# Delete user (Admin only)
# ================================
@router.delete("/users/{user_id}")
async def delete_user_admin(
    user_id: str,
    current_user: dict = Depends(is_admin)
):
    """
    Delete a user account (Admin only).
    
    This also deletes all documents uploaded by the user.
    """
    from src.database.user_db import delete_user as db_delete_user
    from src.database.user_db import get_user_by_id
    
    # Check if user exists
    user = get_user_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with ID '{user_id}' not found"
        )
    
    # Don't allow deleting yourself
    if user_id == current_user.get("user_id"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot delete your own account"
        )
    
    try:
        # Delete user's documents from Qdrant
        client = get_vector_client()
        collection_name = get_collection_name()
        
        # Find all points for this user
        result = client.scroll(
            collection_name=collection_name,
            scroll_filter={
                "must": [{"key": "user_id", "match": {"value": user_id}}]
            },
            limit=10000,
            with_payload=True
        )
        
        points = result[0]
        if points:
            point_ids = [point.id for point in points]
            client.delete(collection_name=collection_name, points_selector=point_ids)
            logger.info(f"Deleted {len(points)} chunks for user {user_id}")
        
        # Delete user from Supabase
        deleted = db_delete_user(user_id)
        
        if not deleted:
            raise Exception("Failed to delete user")
        
        return {
            "status": "success",
            "message": f"User '{user.get('email')}' and their {len(points)} documents deleted successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete user: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete user: {str(e)}"
        )