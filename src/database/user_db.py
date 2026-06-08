from datetime import datetime
from src.database.supabase_client import get_supabase_client
from src.auth.auth import hash_password, verify_password, create_access_token
from src.utils.logger import get_logger

logger = get_logger(__name__)


def create_user(email: str, password: str, name: str = None) -> dict:
    """
    Create a new user account.
    
    Args:
        email: User's email address
        password: Plain text password (will be hashed)
        name: Optional display name
    
    Returns:
        dict: User info (excluding password)
    
    Raises:
        Exception: If email already exists or validation fails
    """
    supabase = get_supabase_client()
    
    # Validate inputs
    if not email or not password:
        raise Exception("Email and password are required")
    
    if len(password) < 4:
        raise Exception("Password must be at least 4 characters")
    
    # REMOVED: bcrypt 72-byte truncation - not needed with sha256_crypt
    
    # Check if user already exists
    try:
        existing = supabase.table("users").select("*").eq("email", email.lower().strip()).execute()
        if existing.data and len(existing.data) > 0:
            raise Exception("User with this email already exists")
    except Exception as e:
        if "User with this email already exists" in str(e):
            raise
        logger.error(f"Error checking existing user: {e}")
        raise Exception("Failed to verify user existence")
    
    # Hash password
    try:
        hashed = hash_password(password)
    except Exception as e:
        logger.error(f"Password hashing failed: {e}")
        raise Exception("Failed to secure password")
    
    # Create user
    user_data = {
        "email": email.lower().strip(),
        "hashed_password": hashed,
        "role": "user",
        "created_at": datetime.utcnow().isoformat(),
        "name": name.strip() if name else None
    }
    
    try:
        result = supabase.table("users").insert(user_data).execute()
    except Exception as e:
        logger.error(f"Supabase insert failed: {e}")
        raise Exception(f"Failed to create user: {str(e)}")
    
    if not result.data or len(result.data) == 0:
        raise Exception("Failed to create user - no data returned")
    
    user = result.data[0]
    
    # Return user without password
    return {
        "id": user["id"],
        "email": user["email"],
        "role": user["role"],
        "created_at": user["created_at"],
        "name": user.get("name")
    }

def get_user_by_email(email: str) -> dict:
    """
    Get user by email address.
    
    Args:
        email: User's email
    
    Returns:
        dict: Full user data (including hashed_password) or None
    """
    supabase = get_supabase_client()
    
    if not email:
        return None
    
    try:
        result = supabase.table("users").select("*").eq("email", email.lower().strip()).execute()
    except Exception as e:
        logger.error(f"Supabase query failed: {e}")
        return None
    
    if not result.data or len(result.data) == 0:
        return None
    
    return result.data[0]


def get_user_by_id(user_id: str) -> dict:
    """
    Get user by ID.
    
    Args:
        user_id: User's UUID
    
    Returns:
        dict: User data or None
    """
    supabase = get_supabase_client()
    
    if not user_id:
        return None
    
    try:
        result = supabase.table("users").select("*").eq("id", user_id).execute()
    except Exception as e:
        logger.error(f"Supabase query failed: {e}")
        return None
    
    if not result.data or len(result.data) == 0:
        return None
    
    return result.data[0]


def authenticate_user(email: str, password: str) -> dict:
    """
    Authenticate user and return token.
    
    Args:
        email: User's email
        password: Plain text password
    
    Returns:
        dict: {"token": jwt_token, "user": user_info}
    
    Raises:
        Exception: Invalid credentials
    """
    if not email or not password:
        raise Exception("Email and password are required")
    
    user = get_user_by_email(email)
    
    if not user:
        raise Exception("Invalid email or password")
    
    # REMOVED: bcrypt 72-byte truncation - not needed with sha256_crypt
    
    try:
        if not verify_password(password, user["hashed_password"]):
            raise Exception("Invalid email or password")
    except Exception as e:
        logger.error(f"Password verification failed for {email}: {e}")
        raise Exception("Invalid email or password")
    
    # Create JWT token
    token_data = {
        "sub": user["id"],
        "email": user["email"],
        "role": user["role"]
    }
    
    try:
        token = create_access_token(token_data)
    except Exception as e:
        logger.error(f"Token creation failed: {e}")
        raise Exception("Failed to create authentication token")
    
    return {
        "token": token,
        "user": {
            "id": user["id"],
            "email": user["email"],
            "role": user["role"],
            "name": user.get("name")
        }
    }

def list_all_users(limit: int = 100) -> list:
    """
    List all users (Admin only).
    
    Args:
        limit: Maximum number of users to return
    
    Returns:
        list: List of user objects (without passwords)
    """
    supabase = get_supabase_client()
    
    try:
        result = supabase.table("users").select("id,email,role,created_at,name").limit(limit).execute()
    except Exception as e:
        logger.error(f"Failed to list users: {e}")
        return []
    
    return result.data if result.data else []


def update_user_role(user_id: str, role: str) -> dict:
    """
    Update user role (Admin only).
    
    Args:
        user_id: User's UUID
        role: New role ("user" or "admin")
    
    Returns:
        dict: Updated user info
    
    Raises:
        Exception: User not found or invalid role
    """
    if role not in ["user", "admin"]:
        raise Exception("Invalid role. Must be 'user' or 'admin'")
    
    supabase = get_supabase_client()
    
    try:
        result = supabase.table("users").update({"role": role}).eq("id", user_id).execute()
    except Exception as e:
        logger.error(f"Failed to update user role: {e}")
        raise Exception(f"Database error: {str(e)}")
    
    if not result.data or len(result.data) == 0:
        raise Exception("User not found")
    
    return result.data[0]


def delete_user(user_id: str) -> bool:
    """
    Delete user account (Admin only).
    
    Args:
        user_id: User's UUID
    
    Returns:
        bool: True if deleted
    """
    supabase = get_supabase_client()
    
    try:
        result = supabase.table("users").delete().eq("id", user_id).execute()
    except Exception as e:
        logger.error(f"Failed to delete user: {e}")
        return False
    
    return len(result.data) > 0 if result.data else False


def update_upload_count(user_id: str, increment: int = 1) -> None:
    """Increment user's upload count for rate limiting."""
    supabase = get_supabase_client()
    
    try:
        # First get current user
        user = get_user_by_id(user_id)
        if not user:
            logger.warning(f"User {user_id} not found for upload count update")
            return
        
        current_count = user.get("total_uploads", 0)
        new_count = current_count + increment
        
        supabase.table("users").update({"total_uploads": new_count}).eq("id", user_id).execute()
    except Exception as e:
        logger.error(f"Failed to update upload count for {user_id}: {e}")


def update_query_count(user_id: str, increment: int = 1) -> None:
    """Increment user's query count for rate limiting."""
    supabase = get_supabase_client()
    
    try:
        # First get current user
        user = get_user_by_id(user_id)
        if not user:
            logger.warning(f"User {user_id} not found for query count update")
            return
        
        current_count = user.get("total_queries", 0)
        new_count = current_count + increment
        
        supabase.table("users").update({"total_queries": new_count}).eq("id", user_id).execute()
    except Exception as e:
        logger.error(f"Failed to update query count for {user_id}: {e}")