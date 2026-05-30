from groq import Groq
from src.config import settings
from src.utils.logger import get_logger

logger = get_logger(__name__)

# ================================
# Single Groq client instance
# ================================
_client = None


def get_llm_client() -> Groq:
    global _client

    if _client is None:
        _client = Groq(api_key=settings.GROQ_API_KEY)
        logger.info(f"Groq client initialized — model: {settings.GROQ_MODEL}")

    return _client


# ================================
# Main entry point
# ================================
def generate_answer(question: str, context_chunks: list[str]) -> str:
    client = get_llm_client()

    context = _build_context(context_chunks)
    prompt = _build_prompt(question, context)

    logger.debug(f"Sending prompt to {settings.GROQ_MODEL}")

    try:
        response = client.chat.completions.create(
            model=settings.GROQ_MODEL,
            messages=[
                {"role": "system", "content": _system_prompt()},
                {"role": "user", "content": prompt}
            ],
            temperature=0.2,
            max_tokens=1000,
        )

        answer = response.choices[0].message.content.strip()
        logger.info(f"Answer generated from Groq")
        return answer

    except Exception as e:
        logger.error(f"Groq API error: {e}")
        raise RuntimeError(f"Failed to generate answer: {str(e)}")


# ================================
# Internal helpers (unchanged)
# ================================
def _system_prompt() -> str:
    return (
        "You are a helpful assistant that answers questions "
        "strictly based on the provided context. "
        "If the answer is not found in the context, say: "
        "'I could not find relevant information in the uploaded documents.' "
        "Never make up information. Never use outside knowledge. "
        "Keep answers clear and concise."
    )


def _build_context(chunks: list[str]) -> str:
    if not chunks:
        return "No relevant context found."

    parts = []
    for i, chunk in enumerate(chunks):
        parts.append(f"[Source {i + 1}]\n{chunk}")

    return "\n\n".join(parts)


def _build_prompt(question: str, context: str) -> str:
    return (
        f"Context:\n"
        f"{context}\n\n"
        f"Question: {question}\n\n"
        f"Answer based only on the context above:"
    )