"""
Logger utility
Centralized logging configuration using loguru
"""

import sys
from pathlib import Path
from loguru import logger

# Remove default handler
logger.remove()

# Add console handler with colors
logger.add(
    sys.stdout,
    colorize=True,
    format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan> - <level>{message}</level>",
    level="INFO"
)

# Add file handler
log_dir = Path(__file__).parent.parent.parent / 'logs'
log_dir.mkdir(exist_ok=True)

logger.add(
    log_dir / "jarvis_{time:YYYY-MM-DD}.log",
    rotation="100 MB",
    retention="7 days",
    compression="zip",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
    level="DEBUG"
)

# Export logger
__all__ = ['logger']
