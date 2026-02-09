"""
News Collector
Collects news from RSS feeds (free sources)
"""

import asyncio
from datetime import datetime
from typing import Dict, List, Any
import feedparser
import aiohttp
from bs4 import BeautifulSoup

from src.utils.logger import logger


class NewsCollector:
    """Collects crypto news from RSS feeds"""
    
    def __init__(self):
        # FREE RSS feeds - Tier 1 (Major)
        self.rss_feeds = {
            "coindesk": "https://www.coindesk.com/arc/outboundfeeds/rss/",
            "cointelegraph": "https://cointelegraph.com/rss",
            "cryptonews": "https://cryptonews.com/news/feed/",
            "bitcoinmagazine": "https://bitcoinmagazine.com/feed",
            "decrypt": "https://decrypt.co/feed",
            # Tier 2 (Additional - more coverage)
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
            'price', 'surge', 'crash', 'rally', 'drop'
        ]
        
    async def collect(self) -> Dict[str, Any]:
        """Collect news from all sources"""
        logger.info("📰 Collecting news from RSS feeds...")
        
        results = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "source": "news_collector",
            "articles": [],
            "sources_checked": len(self.rss_feeds)
        }
        
        # Collect from all RSS feeds
        for source, url in self.rss_feeds.items():
            try:
                articles = await self._collect_rss(source, url)
                results["articles"].extend(articles)
                logger.debug(f"  ✓ {source}: {len(articles)} articles")
            except Exception as e:
                logger.error(f"  ✗ {source}: {e}")
        
        # Sort by published date (newest first)
        results["articles"].sort(
            key=lambda x: x.get('published_at', ''),
            reverse=True
        )
        
        # Keep top 20 most recent
        results["articles"] = results["articles"][:20]
        
        logger.info(f"📰 Collected {len(results['articles'])} articles")
        return results
    
    async def _collect_rss(self, source: str, url: str) -> List[Dict]:
        """Collect from single RSS feed"""
        articles = []
        
        # Parse RSS feed
        loop = asyncio.get_event_loop()
        feed = await loop.run_in_executor(None, feedparser.parse, url)
        
        for entry in feed.entries[:10]:  # Top 10 from each source
            title = entry.get('title', '')
            summary = entry.get('summary', '')
            
            # Check if relevant (contains keywords)
            content_lower = (title + ' ' + summary).lower()
            is_relevant = any(kw in content_lower for kw in self.keywords)
            
            if is_relevant:
                articles.append({
                    "id": f"{source}_{hash(entry.get('link', ''))}",
                    "title": title,
                    "source": source,
                    "url": entry.get('link', ''),
                    "published_at": entry.get('published', ''),
                    "summary": self._clean_html(summary)[:500],
                    "is_relevant": True,
                    "collected_at": datetime.utcnow().isoformat() + "Z"
                })
        
        return articles
    
    def _clean_html(self, html_content: str) -> str:
        """Remove HTML tags from content"""
        if not html_content:
            return ""
        soup = BeautifulSoup(html_content, 'lxml')
        return soup.get_text(separator=' ', strip=True)
    
    def get_top_headlines(self, articles: List[Dict], limit: int = 5) -> List[str]:
        """Get top headlines for AI analysis"""
        headlines = []
        for article in articles[:limit]:
            headlines.append(f"[{article['source']}] {article['title']}")
        return headlines


# Test function
async def test_collector():
    """Test the news collector"""
    collector = NewsCollector()
    data = await collector.collect()
    
    print(f"\n{'='*50}")
    print(f"News Collector Test")
    print(f"{'='*50}")
    print(f"Articles collected: {len(data['articles'])}")
    
    for article in data['articles'][:5]:
        print(f"\n[{article['source']}] {article['title'][:60]}...")


if __name__ == "__main__":
    asyncio.run(test_collector())
