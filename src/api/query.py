from fastapi import APIRouter, Depends, HTTPException, status
from src.core.auth import get_user_role
from src.pipelines.retrieval import retrieve_and_answer
from src.models.schemas import QueryRequest, QueryResponse
from src.utils.logger import get_logger
from src.auth.auth import get_current_user

logger = get_logger(__name__)

router = APIRouter()


# ================================
# Ask a question (Authenticated users)
# ================================
@router.post("/ask", response_model=QueryResponse)
async def ask_question(
    request: QueryRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Ask a question as an authenticated user.
    
    - You must be logged in
    - You see your own documents + public documents
    """
    user_id = current_user.get("user_id")
    user_role = current_user.get("role")
    
    logger.info(
        f"Question received — "
        f"user: {user_id} | "
        f"role: {user_role} | "
        f"top_k: {request.top_k} | "
        f"question: '{request.question}'"
    )

    try:
        result = retrieve_and_answer(
            question=request.question,
            top_k=request.top_k,
            current_user=current_user
        )

        return QueryResponse(
            question=result["question"],
            answer=result["answer"],
            sources=result["sources"],
            model_used=result["model_used"]
        )

    except RuntimeError as e:
        logger.error(f"Retrieval pipeline failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Answer generation is currently unavailable. Please try again."
        )

    except Exception as e:
        logger.error(f"Unexpected error in ask route: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Something went wrong. Please try again."
        )


# ================================
# Ask a question (Public - No login required)
# ================================
@router.post("/ask/public", response_model=QueryResponse)
async def ask_question_public(
    request: QueryRequest,
):
    """
    Ask a question as a public user (no login required).
    
    - No authentication needed
    - Only sees PUBLIC documents (is_private = false)
    """
    logger.info(f"Public question received: '{request.question}'")

    try:
        result = retrieve_and_answer(
            question=request.question,
            top_k=request.top_k,
            current_user=None  # No user = public access
        )

        return QueryResponse(
            question=result["question"],
            answer=result["answer"],
            sources=result["sources"],
            model_used=result["model_used"]
        )
        
    except RuntimeError as e:
        logger.error(f"Public retrieval pipeline failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Answer generation is currently unavailable. Please try again."
        )
        
    except Exception as e:
        logger.error(f"Unexpected error in public ask route: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Something went wrong. Please try again."
        )