"""Processors module init"""

from src.processors.technical_processor import TechnicalProcessor
from src.processors.sentiment_processor import SentimentProcessor
from src.processors.aggregator import DataAggregator

__all__ = ['TechnicalProcessor', 'SentimentProcessor', 'DataAggregator']
