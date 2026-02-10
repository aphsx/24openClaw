"""
News Collector - Hybrid RSS + Web Scraping
Collects crypto news from free sources with anti-blocking.

Strategy:
  1. Collect from RSS feeds (fast, reliable)
  2. If RSS returns < MIN_ARTICLES, supplement with web scraping
  3. Deduplicate by title similarity
"""

import asyncio
import hashlib
from datetime import datetime
from typing import Dict, List, Any
import feedparser
import aiohttp
from bs4 import BeautifulSoup

from src.utils.logger import logger
from src.collectors.news_scraper import NewsScraper


class NewsCollector:
    """Collects crypto news from RSS feeds + web scraping"""

    MIN_ARTICLES = 10  # Minimum before triggering scraper

    def __init__(self):
        # FREE RSS feeds
        self.rss_feeds = {
            # Tier 1: Major
            "coindesk": "https://www.coindesk.com/arc/outboundfeeds/rss/",
            "cointelegraph": "https://cointelegraph.com/rss",
            "cryptonews": "https://cryptonews.com/news/feed/",
            "bitcoinmagazine": "https://bitcoinmagazine.com/feed",
            "decrypt": "https://decrypt.co/feed",
            # Tier 2: Additional coverage
            "theblock": "https://www.theblock.co/rss.xml",
            "blockworks": "https://blockworks.co/feed/",
            "cryptoslate": "https://cryptoslate.com/feed/",
            "newsbtc": "https://www.newsbtc.com/feed/",
            "ambcrypto": "https://ambcrypto.com/feed/",
            "utoday": "https://u.today/rss",
            "beincrypto": "https://beincrypto.com/feed/",
        }

        # Keywords to filter relevant news
        self.keywords = [
            'bitcoin', 'btc', 'ethereum', 'eth', 'crypto',
            'binance', 'exchange', 'regulation', 'sec', 'etf',
            'whale', 'institution', 'adoption', 'bull', 'bear',
            'solana', 'sol', 'xrp', 'ada', 'doge', 'avax',
            'price', 'surge', 'crash', 'rally', 'drop',
            'futures', 'leverage', 'liquidation', 'short', 'long',
            'fed', 'rate', 'inflation', 'market', 'trading',
        ]

        self.scraper = NewsScraper()

    async def collect(self) -> Dict[str, Any]:
        """Collect news from RSS + scraping fallback"""
        logger.info("📰 Collecting news (RSS + scraping)...")

        results = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "source": "news_collector",
            "articles": [],
            "sources_checked": len(self.rss_feeds),
            "collection_methods": [],
        }

        # ── Phase 1: RSS collection ──
        rss_articles = await self._collect_all_rss()
        results["articles"].extend(rss_articles)
        results["collection_methods"].append("rss")

        logger.info(f"  📡 RSS: {len(rss_articles)} articles")

        # ── Phase 2: Scraping if RSS is insufficient ──
        if len(rss_articles) < self.MIN_ARTICLES:
            logger.info("  🌐 RSS insufficient, activating scraper...")
            try:
                scraped_articles = await self.scraper.scrape_all()
                # Filter relevant
                scraped_relevant = [
                    a for a in scraped_articles
                    if self._is_relevant(a.get('title', '') + ' ' + a.get('summary', ''))
                ]
                results["articles"].extend(scraped_relevant)
                results["collection_methods"].append("scrape")
                logger.info(f"  🌐 Scraper: {len(scraped_relevant)} relevant articles")
            except Exception as e:
                logger.error(f"  🌐 Scraper failed: {e}")

        # ── Deduplicate ──
        results["articles"] = self._deduplicate(results["articles"])

        # ── Sort by date (newest first) ──
        results["articles"].sort(
            key=lambda x: x.get('published_at', ''),
            reverse=True
        )

        # ── Keep top 20 ──
        results["articles"] = results["articles"][:20]
        results["total_collected"] = len(results["articles"])

        logger.info(f"📰 Final: {len(results['articles'])} articles "
                     f"({', '.join(results['collection_methods'])})")
        return results

    async def _collect_all_rss(self) -> List[Dict]:
        """Collect from all RSS feeds in parallel batches"""
        articles = []

        # Process in batches of 4 to avoid overwhelming
        feed_items = list(self.rss_feeds.items())
        batch_size = 4

        for i in range(0, len(feed_items), batch_size):
            batch = feed_items[i:i + batch_size]
            tasks = [
                self._collect_rss(source, url)
                for source, url in batch
            ]
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)

            for result in batch_results:
                if isinstance(result, Exception):
                    continue
                articles.extend(result)

        return articles

    async def _collect_rss(self, source: str, url: str) -> List[Dict]:
        """Collect from single RSS feed"""
        articles = []

        try:
            loop = asyncio.get_event_loop()
            feed = await loop.run_in_executor(None, feedparser.parse, url)

            for entry in feed.entries[:10]:
                title = entry.get('title', '')
                summary = entry.get('summary', '')

                # Check relevance
                content_lower = (title + ' ' + summary).lower()
                if not self._is_relevant(content_lower):
                    continue

                articles.append({
                    "id": f"rss_{source}_{hashlib.md5(title.encode()).hexdigest()[:8]}",
                    "title": title,
                    "source": source,
                    "url": entry.get('link', ''),
                    "published_at": entry.get('published', ''),
                    "summary": self._clean_html(summary)[:500],
                    "is_relevant": True,
                    "collected_at": datetime.utcnow().isoformat() + "Z",
                    "collection_method": "rss",
                })

            logger.debug(f"  ✓ {source}: {len(articles)} articles")

        except Exception as e:
            logger.error(f"  ✗ {source}: {e}")

        return articles

    def _is_relevant(self, text: str) -> bool:
        """Check if text contains relevant keywords"""
        text_lower = text.lower()
        return any(kw in text_lower for kw in self.keywords)

    def _clean_html(self, html_content: str) -> str:
        """Remove HTML tags from content"""
        if not html_content:
            return ""
        soup = BeautifulSoup(html_content, 'lxml')
        return soup.get_text(separator=' ', strip=True)

    def _deduplicate(self, articles: List[Dict]) -> List[Dict]:
        """Remove duplicate articles by title similarity"""
        seen_titles = set()
        unique = []

        for article in articles:
            # Normalize title for comparison
            title_key = article.get('title', '').lower().strip()[:60]
            title_hash = hashlib.md5(title_key.encode()).hexdigest()

            if title_hash not in seen_titles:
                seen_titles.add(title_hash)
                unique.append(article)

        return unique

    def get_top_headlines(self, articles: List[Dict], limit: int = 5) -> List[str]:
        """Get top headlines for AI analysis"""
        headlines = []
        for article in articles[:limit]:
            headlines.append(f"[{article['source']}] {article['title']}")
        return headlines

    async def close(self):
        """Cleanup resources"""
        await self.scraper.close()


# Test function
async def test_collector():
    """Test the news collector"""
    collector = NewsCollector()

    try:
        data = await collector.collect()

        print(f"\n{'='*60}")
        print(f"News Collector Test (Hybrid RSS + Scraping)")
        print(f"{'='*60}")
        print(f"Total articles: {data['total_collected']}")
        print(f"Methods used: {data['collection_methods']}")

        for article in data['articles'][:5]:
            method = article.get('collection_method', '?')
            print(f"\n[{method}][{article['source']}] {article['title'][:70]}...")
    finally:
        await collector.close()


if __name__ == "__main__":
    asyncio.run(test_collector())
