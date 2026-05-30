from fastapi import UploadFile, HTTPException, status
from src.config import settings
from src.core.auth import UserRole
from src.utils.logger import get_logger

logger = get_logger(__name__)


# ================================
# Main entry point
# ================================
def validate_upload(files: list[UploadFile], role: str) -> None:
    if role == UserRole.ADMIN:
        logger.debug("Admin upload — skipping all limits")
        return

    _check_file_count(files)

    for file in files:
        _check_extension(file.filename)
        _check_file_size(file)


# ================================
# Internal checks
# ================================
def _check_file_count(files: list[UploadFile]) -> None:
    max_files = settings.PUBLIC_MAX_FILES_COUNT

    if len(files) > max_files:
        logger.warning(
            f"Public user exceeded file count limit: "
            f"{len(files)} files, max is {max_files}"
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Maximum {max_files} files allowed per upload"
        )


def _check_extension(filename: str) -> None:
    allowed = settings.get_allowed_extensions()

    if "." not in filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File '{filename}' has no extension"
        )

    extension = filename.rsplit(".", 1)[-1].lower()

    if extension not in allowed:
        logger.warning(
            f"Public user tried to upload disallowed type: .{extension}"
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"File type '.{extension}' is not allowed. "
                f"Allowed types: {', '.join(allowed)}"
            )
        )


def _check_file_size(file: UploadFile) -> None:
    max_bytes = settings.get_max_file_size_bytes()

    # content-length header check (fast, not always present)
    if file.size is not None and file.size > max_bytes:
        logger.warning(
            f"Public user exceeded file size limit: "
            f"{file.size} bytes, max is {max_bytes}"
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"File '{file.filename}' exceeds maximum size of "
                f"{settings.PUBLIC_MAX_FILE_SIZE_MB}MB"
            )
        )