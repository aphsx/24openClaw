"""Collectors module init"""

from src.collectors.binance_collector import BinanceCollector
from src.collectors.news_collector import NewsCollector
from src.collectors.news_scraper import NewsScraper
from src.collectors.onchain_collector import OnchainCollector

__all__ = ['BinanceCollector', 'NewsCollector', 'NewsScraper', 'OnchainCollector']
