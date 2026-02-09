"""Utils module init"""

from src.utils.config import config
from src.utils.logger import logger
from src.utils.telegram_notifier import telegram

__all__ = ['config', 'logger', 'telegram']
