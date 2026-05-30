from fastapi import Header, HTTPException, status
from src.config import settings
from src.utils.logger import get_logger

logger = get_logger(__name__)


# ================================
# Role definition
# ================================
class UserRole:
    ADMIN = "admin"
    PUBLIC = "public"


# ================================
# Role detection
# ================================
def get_user_role(x_admin_password: str | None = Header(default=None)) -> str:
    if x_admin_password is None:
        logger.debug("No password header — public user")
        return UserRole.PUBLIC

    if x_admin_password == settings.ADMIN_PASSWORD:
        logger.debug("Valid admin password — admin user")
        return UserRole.ADMIN

    logger.warning("Invalid admin password attempt")
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid admin password"
    )


# ================================
# Hard guard — admin only routes
# ================================
def require_admin(role: str) -> None:
    if role != UserRole.ADMIN:
        logger.warning("Unauthorized access attempt to admin route")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )