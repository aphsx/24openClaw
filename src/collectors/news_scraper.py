"""
News Scraper - Web scraping with anti-blocking
Scrapes crypto news from websites when RSS fails or returns too few articles.

Strategy:
  1. Primary: httpx + BeautifulSoup (lightweight, fast)
  2. Fallback: Playwright headless (for JS-rendered sites)

Anti-blocking:
  - Random User-Agent rotation
  - Random delays between requests (2-5s)
  - Stealth Playwright launch args
  - Request headers mimicking real browsers
"""

import asyncio
import random
import hashlib
from datetime import datetime
from typing import Dict, List, Any, Optional

import httpx
from bs4 import BeautifulSoup

from src.utils.logger import logger

# Try to import fake_useragent, fallback to built-in list
try:
    from fake_useragent import UserAgent
    _ua = UserAgent()
    def _random_ua() -> str:
        return _ua.random
except ImportError:
    _UA_LIST = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36 Edg/119.0.0.0",
    ]
    def _random_ua() -> str:
        return random.choice(_UA_LIST)


# ============================================================
# Site-specific scrapers
# ============================================================

SCRAPE_TARGETS = {
    "coindesk": {
        "url": "https://www.coindesk.com/markets/",
        "needs_js": False,
        "selectors": {
            "articles": "div.article-card, article, div[class*='Card']",
            "title": "h2, h3, h4, a[class*='heading'], a[class*='title']",
            "link": "a[href]",
            "summary": "p, span[class*='description'], span[class*='excerpt']",
        },
    },
    "cointelegraph": {
        "url": "https://cointelegraph.com/tags/bitcoin",
        "needs_js": False,
        "selectors": {
            "articles": "article, li[class*='post'], div[class*='post-card']",
            "title": "a[class*='title'], h2, span[class*='title']",
            "link": "a[href]",
            "summary": "p[class*='lead'], p[class*='excerpt']",
        },
    },
    "cryptonews": {
        "url": "https://cryptonews.com/news/",
        "needs_js": False,
        "selectors": {
            "articles": "div.cn-tile, article, div[class*='article']",
            "title": "h4 a, h3 a, a[class*='title']",
            "link": "a[href]",
            "summary": "p, div[class*='lead']",
        },
    },
}


class NewsScraper:
    """Scrapes crypto news with anti-blocking measures"""

    def __init__(self):
        self._browser = None  # Reuse Playwright browser instance
        self._playwright = None
        self.min_delay = 2.0  # seconds between requests
        self.max_delay = 5.0
        self.timeout = 15.0   # request timeout

    def _get_headers(self) -> dict:
        """Generate randomized browser-like headers"""
        return {
            "User-Agent": _random_ua(),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "DNT": "1",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
            "Cache-Control": "max-age=0",
        }

    async def _random_delay(self):
        """Random delay to mimic human browsing"""
        delay = random.uniform(self.min_delay, self.max_delay)
        await asyncio.sleep(delay)

    # --------------------------------------------------------
    # Primary: httpx + BeautifulSoup
    # --------------------------------------------------------

    async def scrape_all(self) -> List[Dict]:
        """Scrape all target sites using httpx (lightweight)"""
        all_articles = []

        async with httpx.AsyncClient(
            follow_redirects=True,
            timeout=httpx.Timeout(self.timeout),
            http2=True,
        ) as client:
            for source_name, target in SCRAPE_TARGETS.items():
                try:
                    articles = await self._scrape_site(client, source_name, target)
                    all_articles.extend(articles)
                    logger.debug(f"  🌐 Scraped {source_name}: {len(articles)} articles")
                except Exception as e:
                    logger.warning(f"  🌐 Scrape {source_name} failed (httpx): {e}")
                    # Try Playwright fallback for JS-heavy sites
                    if target.get("needs_js", False):
                        try:
                            articles = await self._scrape_with_browser(
                                source_name, target["url"], target["selectors"]
                            )
                            all_articles.extend(articles)
                            logger.debug(f"  🎭 Playwright {source_name}: {len(articles)} articles")
                        except Exception as e2:
                            logger.error(f"  🎭 Playwright {source_name} also failed: {e2}")

                await self._random_delay()

        return all_articles

    async def _scrape_site(
        self, client: httpx.AsyncClient, source: str, target: dict
    ) -> List[Dict]:
        """Scrape a single site with httpx"""
        headers = self._get_headers()
        response = await client.get(target["url"], headers=headers)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "lxml")
        articles = []
        selectors = target["selectors"]

        # Find article containers
        containers = soup.select(selectors["articles"])[:15]

        for container in containers:
            # Extract title
            title_el = container.select_one(selectors["title"])
            if not title_el:
                continue
            title = title_el.get_text(strip=True)
            if not title or len(title) < 10:
                continue

            # Extract link
            link_el = container.select_one(selectors["link"])
            link = ""
            if link_el and link_el.get("href"):
                link = link_el["href"]
                if link.startswith("/"):
                    # Make absolute URL
                    from urllib.parse import urljoin
                    link = urljoin(target["url"], link)

            # Extract summary
            summary = ""
            summary_el = container.select_one(selectors["summary"])
            if summary_el:
                summary = summary_el.get_text(strip=True)[:500]

            article_id = hashlib.md5(
                (source + title).encode()
            ).hexdigest()[:12]

            articles.append({
                "id": f"scrape_{source}_{article_id}",
                "title": title,
                "source": f"{source}_scrape",
                "url": link,
                "published_at": datetime.utcnow().isoformat() + "Z",
                "summary": summary,
                "is_relevant": True,
                "collected_at": datetime.utcnow().isoformat() + "Z",
                "collection_method": "scrape",
            })

        return articles

    # --------------------------------------------------------
    # Fallback: Playwright (JS-rendered sites)
    # --------------------------------------------------------

    async def _ensure_browser(self):
        """Lazily create Playwright browser (reuse across calls)"""
        if self._browser is not None:
            return self._browser

        try:
            from playwright.async_api import async_playwright

            self._playwright = await async_playwright().start()
            self._browser = await self._playwright.chromium.launch(
                headless=True,
                args=[
                    "--no-sandbox",
                    "--disable-setuid-sandbox",
                    "--disable-dev-shm-usage",       # Save RAM on VPS
                    "--disable-accelerated-2d-canvas",
                    "--disable-gpu",
                    "--single-process",              # Save RAM
                    "--no-zygote",                    # Save RAM
                    "--disable-background-networking",
                    "--disable-extensions",
                    "--disable-sync",
                    "--disable-translate",
                    "--disable-default-apps",
                    "--window-size=1920,1080",
                ],
            )
            logger.info("🎭 Playwright browser launched (stealth mode)")
            return self._browser

        except Exception as e:
            logger.error(f"Failed to launch Playwright: {e}")
            return None

    async def _scrape_with_browser(
        self, source: str, url: str, selectors: dict
    ) -> List[Dict]:
        """Scrape using Playwright for JS-rendered pages"""
        browser = await self._ensure_browser()
        if not browser:
            return []

        context = await browser.new_context(
            user_agent=_random_ua(),
            viewport={"width": 1920, "height": 1080},
            locale="en-US",
            timezone_id="America/New_York",
            # Extra stealth
            extra_http_headers={
                "Accept-Language": "en-US,en;q=0.9",
                "DNT": "1",
            },
        )

        page = await context.new_page()

        # Block unnecessary resources to save bandwidth + speed
        await page.route(
            "**/*.{png,jpg,jpeg,gif,svg,ico,woff,woff2,ttf,eot}",
            lambda route: route.abort(),
        )
        await page.route("**/*analytics*", lambda route: route.abort())
        await page.route("**/*tracking*", lambda route: route.abort())
        await page.route("**/*ads*", lambda route: route.abort())

        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=20000)
            await page.wait_for_timeout(3000)  # Wait for dynamic content

            content = await page.content()
            soup = BeautifulSoup(content, "lxml")

            articles = []
            containers = soup.select(selectors["articles"])[:15]

            for container in containers:
                title_el = container.select_one(selectors["title"])
                if not title_el:
                    continue
                title = title_el.get_text(strip=True)
                if not title or len(title) < 10:
                    continue

                link_el = container.select_one(selectors["link"])
                link = ""
                if link_el and link_el.get("href"):
                    link = link_el["href"]
                    if link.startswith("/"):
                        from urllib.parse import urljoin
                        link = urljoin(url, link)

                summary_el = container.select_one(selectors["summary"])
                summary = summary_el.get_text(strip=True)[:500] if summary_el else ""

                article_id = hashlib.md5(
                    (source + title).encode()
                ).hexdigest()[:12]

                articles.append({
                    "id": f"pw_{source}_{article_id}",
                    "title": title,
                    "source": f"{source}_playwright",
                    "url": link,
                    "published_at": datetime.utcnow().isoformat() + "Z",
                    "summary": summary,
                    "is_relevant": True,
                    "collected_at": datetime.utcnow().isoformat() + "Z",
                    "collection_method": "playwright",
                })

            return articles

        except Exception as e:
            logger.error(f"Playwright scrape error for {source}: {e}")
            return []
        finally:
            await page.close()
            await context.close()

    async def close(self):
        """Cleanup browser resources"""
        if self._browser:
            await self._browser.close()
            self._browser = None
        if self._playwright:
            await self._playwright.stop()
            self._playwright = None
