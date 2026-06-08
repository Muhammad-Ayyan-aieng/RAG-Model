from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, EmailStr
from src.database.user_db import create_user, authenticate_user
from src.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/auth", tags=["Authentication"])


# ================================
# Request/Response Models
# ================================
class SignupRequest(BaseModel):
    email: EmailStr
    password: str
    name: str = None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class AuthResponse(BaseModel):
    token: str
    user: dict


class MessageResponse(BaseModel):
    message: str


# ================================
# Endpoints
# ================================
@router.post("/signup", response_model=AuthResponse)
async def signup(request: SignupRequest):
    """
    Register a new user account.
    
    - Valid email required
    - Password will be hashed (not stored as plain text)
    - Returns JWT token for immediate login
    """
    logger.info(f"Signup attempt: {request.email}")
    
    try:
        user = create_user(
            email=request.email,
            password=request.password,
            name=request.name
        )
        
        # Login immediately after signup
        auth_result = authenticate_user(request.email, request.password)
        
        logger.info(f"User created: {request.email}")
        
        return AuthResponse(
            token=auth_result["token"],
            user=auth_result["user"]
        )
        
    except Exception as e:
        logger.error(f"Signup failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/login", response_model=AuthResponse)
async def login(request: LoginRequest):
    """
    Login with email and password.
    
    - Returns JWT token for subsequent API calls
    - Token must be included in Authorization header
    """
    logger.info(f"Login attempt: {request.email}")
    
    try:
        result = authenticate_user(request.email, request.password)
        
        logger.info(f"User logged in: {request.email}")
        
        return AuthResponse(
            token=result["token"],
            user=result["user"]
        )
        
    except Exception as e:
        logger.error(f"Login failed for {request.email}: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )