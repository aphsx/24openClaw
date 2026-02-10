"""
ClawBot AI — Logger Module
Loguru-based logging with file rotation
"""
import sys
from loguru import logger

from src.utils.config import settings


def setup_logger():
    """Configure loguru logger."""
    logger.remove()  # Remove default handler

    # Console output
    logger.add(
        sys.stdout,
        level=settings.LOG_LEVEL,
        format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan> - <level>{message}</level>",
        colorize=True,
    )

    # File output with rotation
    logger.add(
        settings.LOG_FILE,
        level="DEBUG",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
        rotation="10 MB",
        retention="7 days",
        compression="zip",
    )

    return logger


# Setup on import
log = setup_logger()
