import fitz  # PyMuPDF
from fastapi import UploadFile
from src.config import settings


# ================================
# Main entry point
# ================================
async def extract_text(file: UploadFile) -> str:
    extension = _get_extension(file.filename)
    _validate_extension(extension)

    content = await file.read()

    if extension == "pdf":
        return _parse_pdf(content)
    elif extension == "txt":
        return _parse_txt(content)


# ================================
# Internal helpers
# ================================
def _get_extension(filename: str) -> str:
    if "." not in filename:
        raise ValueError(f"File '{filename}' has no extension")
    return filename.rsplit(".", 1)[-1].lower()


def _validate_extension(extension: str) -> None:
    allowed = settings.get_allowed_extensions()
    if extension not in allowed:
        raise ValueError(
            f"File type '.{extension}' is not allowed. "
            f"Allowed types: {', '.join(allowed)}"
        )


def _parse_pdf(content: bytes) -> str:
    text_parts = []

    with fitz.open(stream=content, filetype="pdf") as doc:
        for page_num, page in enumerate(doc):
            page_text = page.get_text("text")
            if page_text.strip():
                text_parts.append(f"[Page {page_num + 1}]\n{page_text}")

    if not text_parts:
        raise ValueError(
            "PDF appears to be empty or is a scanned image. "
            "Only text-based PDFs are supported."
        )

    return "\n\n".join(text_parts)


def _parse_txt(content: bytes) -> str:
    try:
        text = content.decode("utf-8")
    except UnicodeDecodeError:
        text = content.decode("latin-1")

    if not text.strip():
        raise ValueError("Text file is empty")

    return text