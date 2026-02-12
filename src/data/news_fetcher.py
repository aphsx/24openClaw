"""
ClawBot AI — News Fetcher
Free sources: CryptoPanic API, CryptoPanic RSS, free-crypto-news, CoinDesk RSS, CoinTelegraph RSS, Binance Blog RSS
"""
import asyncio
import xml.etree.ElementTree as ET
import re
import html
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import aiohttp
import feedparser

from src.utils.config import settings
from src.utils.logger import log


class NewsFetcher:
    """Fetch crypto news from multiple free sources asynchronously."""

    RSS_FEEDS = {
        "CoinDesk": "https://www.coindesk.com/arc/outboundfeeds/rss/",
        "CoinTelegraph": "https://cointelegraph.com/rss",
        "Binance Blog": "https://www.binance.com/en/feed/rss",
    }

    def __init__(self):
        self._session: Optional[aiohttp.ClientSession] = None
        self._news_cache: List[dict] = []
        self._cache_timestamp: Optional[datetime] = None

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=settings.NEWS_TIMEOUT_SECONDS)
            )
        return self._session

    async def close(self):
        if self._session and not self._session.closed:
            await self._session.close()

    async def fetch_all(self) -> List[dict]:
        """
        Fetch news from all sources in parallel.
        Returns list of news dicts sorted by timestamp (newest first).
        If fetch fails or is too slow, returns cached news.
        """
        try:
            tasks = [
                self._fetch_cryptopanic(),
                self._fetch_free_crypto_news(),
                *[self._fetch_rss(name, url) for name, url in self.RSS_FEEDS.items()],
            ]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            all_news = []
            for result in results:
                if isinstance(result, list):
                    all_news.extend(result)
                elif isinstance(result, Exception):
                    log.warning(f"News source failed: {result}")

            # Deduplicate by title similarity
            seen_titles = set()
            unique_news = []
            for n in all_news:
                title_key = n.get("title", "")[:50].lower()
                if title_key not in seen_titles:
                    seen_titles.add(title_key)
                    unique_news.append(n)

            # Sort by timestamp (newest first)
            unique_news.sort(key=lambda x: x.get("timestamp", ""), reverse=True)

            # Take top N
            result = unique_news[:settings.NEWS_COUNT]

            if result:
                self._news_cache = result
                self._cache_timestamp = datetime.now(timezone.utc)
                return result

        except Exception as e:
            log.error(f"News fetch error: {e}")

        # Fallback to cache
        if self._news_cache:
            log.warning("Using cached news")
            return self._news_cache

        return []

    def get_cached(self) -> tuple:
        """Get cached news and whether it's actually cached."""
        return self._news_cache, self._cache_timestamp

    async def _fetch_cryptopanic(self) -> List[dict]:
        """Fetch from CryptoPanic API (free tier)."""
        session = await self._get_session()
        try:
            params = {"public": "true", "metadata": "true"}
            if settings.CRYPTOPANIC_API_KEY:
                params["auth_token"] = settings.CRYPTOPANIC_API_KEY
            
            url = "https://cryptopanic.com/api/v1/posts/"
            
            async with session.get(url, params=params) as resp:
                if resp.status != 200:
                    return []
                data = await resp.json()
                results = data.get("results", [])
                
                news_list = []
                for r in results[:10]:
                    votes = r.get("votes", {})
                    positive = votes.get("positive", 0)
                    negative = votes.get("negative", 0)
                    important = votes.get("important", 0)
                    sentiment = "Neutral"
                    if positive > negative and positive > important:
                        sentiment = "Positive"
                    elif negative > positive and negative > important:
                        sentiment = "Negative"
                    elif important > positive and important > negative:
                        sentiment = "Important"
                        
                    title = r.get("title", "")
                    desc = ""
                    if "metadata" in r and "description" in r["metadata"]:
                        desc = r["metadata"]["description"]
                    
                    news_list.append({
                        "title": title,
                        "description": desc,
                        "sentiment": sentiment,
                        "votes": f"pos:{positive} neg:{negative} imp:{important}",
                        "source": r.get("source", {}).get("title", "CryptoPanic"),
                        "timestamp": r.get("published_at", ""),
                        "url": r.get("url", ""),
                    })
                return news_list
        except Exception as e:
            log.debug(f"CryptoPanic API failed: {e}")
            return []

    async def _fetch_free_crypto_news(self) -> List[dict]:
        """Fetch from free-crypto-news API (no key needed)."""
        session = await self._get_session()
        try:
            url = "https://free-crypto-news.vercel.app/api/general"
            async with session.get(url) as resp:
                if resp.status != 200:
                    return []
                data = await resp.json()
                if not isinstance(data, list):
                    data = data.get("articles", data.get("data", []))
                return [
                    {
                        "title": a.get("title", ""),
                        "source": a.get("source", "free-crypto-news"),
                        "timestamp": a.get("date", a.get("publishedAt", "")),
                        "url": a.get("url", a.get("link", "")),
                    }
                    for a in (data if isinstance(data, list) else [])[:10]
                ]
        except Exception as e:
            log.debug(f"free-crypto-news failed: {e}")
            return []

    async def _fetch_rss(self, source_name: str, url: str) -> List[dict]:
        """Fetch and parse RSS feed using feedparser."""
        session = await self._get_session()
        try:
            async with session.get(url) as resp:
                if resp.status != 200:
                    return []
                text = await resp.text()
                
                feed = feedparser.parse(text)
                results = []
                
                for entry in feed.entries[:8]:
                    title = entry.get("title", "")
                    link = entry.get("link", "")
                    desc = entry.get("summary", entry.get("description", ""))
                    
                    if desc:
                        desc = re.sub(r'<[^>]+>', '', desc)
                        desc = html.unescape(desc).strip()
                        if len(desc) > 200:
                            desc = desc[:200] + "..."
                    
                    pub_date = entry.get("published", entry.get("updated", ""))
                    
                    results.append({
                        "title": title,
                        "description": desc or "",
                        "source": source_name,
                        "timestamp": pub_date,
                        "url": link
                    })
                return results

        except Exception as e:
            log.debug(f"RSS {source_name} failed: {e}")
            return []


class FearGreedFetcher:
    """Fetch Fear & Greed Index from Alternative.me (free, unlimited)."""

    URL = "https://api.alternative.me/fng/"

    async def fetch(self) -> Dict[str, Any]:
        """
        Returns: {"value": 68, "label": "Greed", "timestamp": "..."}
        Value 0-100:
          0-24  = Extreme Fear (อาจเป็นจุดซื้อ)
          25-44 = Fear
          45-55 = Neutral
          56-74 = Greed
          75-100 = Extreme Greed (อาจเป็นจุดขาย)
        """
        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=5)) as session:
                async with session.get(self.URL) as resp:
                    if resp.status != 200:
                        return {"value": 50, "label": "Neutral"}
                    data = await resp.json()
                    item = data.get("data", [{}])[0]
                    value = int(item.get("value", 50))
                    label = item.get("value_classification", "Neutral")
                    ts = item.get("timestamp", "")
                    return {"value": value, "label": label, "timestamp": ts}
        except Exception as e:
            log.warning(f"Fear & Greed fetch failed: {e}")
            return {"value": 50, "label": "Neutral"}
