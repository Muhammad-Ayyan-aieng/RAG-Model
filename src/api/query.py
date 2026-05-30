from fastapi import APIRouter, Depends, HTTPException, status
from src.core.auth import get_user_role
from src.pipelines.retrieval import retrieve_and_answer
from src.models.schemas import QueryRequest, QueryResponse
from src.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter()


# ================================
# Ask a question
# ================================
@router.post("/ask", response_model=QueryResponse)
async def ask_question(
    request: QueryRequest,
    role: str = Depends(get_user_role)
):
    logger.info(
        f"Question received — "
        f"role: {role} | "
        f"top_k: {request.top_k} | "
        f"question: '{request.question}'"
    )

    try:
        result = retrieve_and_answer(
            question=request.question,
            top_k=request.top_k
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