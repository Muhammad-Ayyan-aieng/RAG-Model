import logging
import sys
from src.config import settings


# ================================
# Log format
# ================================
DEV_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
PROD_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


# ================================
# Setup function — called once
# ================================
def setup_logging() -> None:
    level = logging.DEBUG if not settings.is_production() else logging.INFO

    formatter = logging.Formatter(
        fmt=DEV_FORMAT if not settings.is_production() else PROD_FORMAT,
        datefmt=DATE_FORMAT
    )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    # avoid adding duplicate handlers if called more than once
    if not root_logger.handlers:
        root_logger.addHandler(handler)

    # silence noisy third party loggers
    logging.getLogger("chromadb").setLevel(logging.WARNING)
    logging.getLogger("sentence_transformers").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)


# ================================
# Factory — used everywhere
# ================================
def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)