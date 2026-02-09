"""
Sentiment Processor
Uses AI to analyze news and determine market sentiment
Supports Claude (Anthropic) and Kimi (Moonshot) - both FREE tier
"""

import asyncio
from datetime import datetime
from typing import Dict, List, Any
import httpx

from src.utils.config import config
from src.utils.logger import logger


class SentimentProcessor:
    """Processes news into sentiment analysis using AI"""
    
    def __init__(self):
        self.primary_model = config.PRIMARY_AI_MODEL  # claude or kimi
        self.backup_model = config.BACKUP_AI_MODEL
        
    async def process(self, raw_news_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process news into sentiment analysis"""
        logger.info("🧠 Processing sentiment with AI...")
        
        articles = raw_news_data.get('articles', [])
        
        if not articles:
            logger.warning("No articles to analyze")
            return self._empty_result()
        
        # Build headlines summary
        headlines = self._build_headlines_text(articles)
        
        # Try primary model first
        try:
            analysis = await self._analyze_with_ai(headlines, self.primary_model)
        except Exception as e:
            logger.warning(f"Primary model ({self.primary_model}) failed: {e}")
            # Fallback to backup model
            try:
                analysis = await self._analyze_with_ai(headlines, self.backup_model)
            except Exception as e2:
                logger.error(f"Backup model ({self.backup_model}) failed: {e2}")
                return self._fallback_analysis(articles)
        
        # Combine with article-level sentiment
        result = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "source": "sentiment_processor",
            "ai_model": self.primary_model,
            "overall_sentiment": analysis.get('overall_sentiment', {}),
            "news_analysis": self._create_news_analysis(articles, analysis),
            "key_topics": analysis.get('key_topics', []),
            "narrative": analysis.get('narrative', 'Unable to generate narrative'),
            "article_count": len(articles)
        }
        
        logger.info(f"🧠 Sentiment: {result['overall_sentiment'].get('label', 'N/A')} "
                   f"(Score: {result['overall_sentiment'].get('score', 0)})")
        
        return result
    
    def _build_headlines_text(self, articles: List[Dict]) -> str:
        """Build text from headlines for analysis"""
        lines = []
        for i, article in enumerate(articles[:15], 1):
            source = article.get('source', 'Unknown')
            title = article.get('title', '')
            lines.append(f"{i}. [{source}] {title}")
        return "\n".join(lines)
    
    async def _analyze_with_ai(self, headlines: str, model: str) -> Dict:
        """Analyze headlines with specified AI model"""
        
        prompt = f"""Analyze the following crypto news headlines and provide sentiment analysis.

Headlines:
{headlines}

Respond in this exact JSON format:
{{
  "overall_sentiment": {{
    "score": <0-100, where 0=very bearish, 50=neutral, 100=very bullish>,
    "label": "<BEARISH|NEUTRAL_BEARISH|NEUTRAL|NEUTRAL_BULLISH|BULLISH>",
    "confidence": <0.0-1.0>
  }},
  "key_topics": ["topic1", "topic2", "topic3"],
  "narrative": "<one sentence summary of market sentiment>",
  "top_bullish": "<most bullish headline>",
  "top_bearish": "<most bearish headline if any>"
}}

Only respond with valid JSON, no other text."""

        if model == "claude":
            return await self._call_claude(prompt)
        elif model == "kimi":
            return await self._call_kimi(prompt)
        elif model == "groq":
            return await self._call_groq(prompt)
        else:
            raise ValueError(f"Unknown model: {model}")
    
    async def _call_claude(self, prompt: str) -> Dict:
        """Call Claude API (Anthropic)"""
        if not config.ANTHROPIC_API_KEY:
            raise ValueError("ANTHROPIC_API_KEY not configured")
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": config.ANTHROPIC_API_KEY,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json"
                },
                json={
                    "model": "claude-3-haiku-20240307",  # Free tier friendly
                    "max_tokens": 500,
                    "messages": [
                        {"role": "user", "content": prompt}
                    ]
                },
                timeout=30.0
            )
            
            if response.status_code != 200:
                raise Exception(f"Claude API error: {response.status_code}")
            
            data = response.json()
            text = data['content'][0]['text']
            
            # Parse JSON from response
            return self._parse_json_response(text)
    
    async def _call_kimi(self, prompt: str) -> Dict:
        """Call Kimi API (Moonshot)"""
        if not config.KIMI_API_KEY:
            raise ValueError("KIMI_API_KEY not configured")
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.moonshot.cn/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {config.KIMI_API_KEY}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "moonshot-v1-8k",  # Free tier
                    "messages": [
                        {"role": "user", "content": prompt}
                    ],
                    "temperature": 0.3
                },
                timeout=30.0
            )
            
            if response.status_code != 200:
                raise Exception(f"Kimi API error: {response.status_code}")
            
            data = response.json()
            text = data['choices'][0]['message']['content']
            
            return self._parse_json_response(text)
    
    async def _call_groq(self, prompt: str) -> Dict:
        """Call Groq API (FREE - Llama 3.1)"""
        groq_key = getattr(config, 'GROQ_API_KEY', '')
        if not groq_key:
            raise ValueError("GROQ_API_KEY not configured")
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {groq_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "llama-3.1-70b-versatile",  # FREE tier
                    "messages": [
                        {"role": "user", "content": prompt}
                    ],
                    "temperature": 0.3
                },
                timeout=30.0
            )
            
            if response.status_code != 200:
                raise Exception(f"Groq API error: {response.status_code}")
            
            data = response.json()
            text = data['choices'][0]['message']['content']
            
            return self._parse_json_response(text)
    
    def _parse_json_response(self, text: str) -> Dict:
        """Parse JSON from AI response"""
        import json
        
        # Find JSON in response
        start = text.find('{')
        end = text.rfind('}') + 1
        
        if start == -1 or end == 0:
            raise ValueError("No JSON found in response")
        
        json_str = text[start:end]
        return json.loads(json_str)
    
    def _fallback_analysis(self, articles: List[Dict]) -> Dict:
        """Fallback sentiment analysis without AI"""
        logger.warning("Using fallback sentiment analysis")
        
        # Simple keyword-based analysis
        bullish_keywords = ['surge', 'rally', 'bull', 'gain', 'rise', 'up', 'high', 'record', 'approval', 'adopt']
        bearish_keywords = ['crash', 'drop', 'bear', 'fall', 'down', 'low', 'decline', 'reject', 'ban', 'hack']
        
        bullish_count = 0
        bearish_count = 0
        
        for article in articles:
            title = article.get('title', '').lower()
            for kw in bullish_keywords:
                if kw in title:
                    bullish_count += 1
            for kw in bearish_keywords:
                if kw in title:
                    bearish_count += 1
        
        total = bullish_count + bearish_count
        if total == 0:
            score = 50
            label = "NEUTRAL"
        else:
            score = int((bullish_count / total) * 100)
            if score >= 70:
                label = "BULLISH"
            elif score >= 55:
                label = "NEUTRAL_BULLISH"
            elif score <= 30:
                label = "BEARISH"
            elif score <= 45:
                label = "NEUTRAL_BEARISH"
            else:
                label = "NEUTRAL"
        
        return {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "source": "sentiment_processor",
            "ai_model": "fallback_keywords",
            "overall_sentiment": {
                "score": score,
                "label": label,
                "confidence": 0.5
            },
            "news_analysis": [],
            "key_topics": [],
            "narrative": f"Keyword analysis: {bullish_count} bullish, {bearish_count} bearish signals",
            "article_count": len(articles)
        }
    
    def _create_news_analysis(self, articles: List[Dict], ai_analysis: Dict) -> List[Dict]:
        """Create per-article analysis"""
        result = []
        for article in articles[:10]:
            result.append({
                "article_id": article.get('id', ''),
                "title": article.get('title', ''),
                "source": article.get('source', ''),
                "published_at": article.get('published_at', '')
            })
        return result
    
    def _empty_result(self) -> Dict:
        """Return empty result"""
        return {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "source": "sentiment_processor",
            "ai_model": "none",
            "overall_sentiment": {"score": 50, "label": "NEUTRAL", "confidence": 0},
            "news_analysis": [],
            "key_topics": [],
            "narrative": "No news data available",
            "article_count": 0
        }


# Test function
async def test_processor():
    """Test the sentiment processor"""
    sample_news = {
        "articles": [
            {"id": "1", "title": "Bitcoin ETF sees record inflows as prices surge", "source": "CoinDesk"},
            {"id": "2", "title": "Ethereum upgrade expected to boost network performance", "source": "Cointelegraph"},
            {"id": "3", "title": "Crypto market shows signs of recovery amid positive sentiment", "source": "CryptoNews"}
        ]
    }
    
    processor = SentimentProcessor()
    result = await processor.process(sample_news)
    
    print(f"\n{'='*50}")
    print("Sentiment Processor Test")
    print(f"{'='*50}")
    print(f"Score: {result['overall_sentiment']['score']}")
    print(f"Label: {result['overall_sentiment']['label']}")
    print(f"Narrative: {result['narrative']}")


if __name__ == "__main__":
    asyncio.run(test_processor())
