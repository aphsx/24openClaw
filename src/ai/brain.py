"""
ClawBot AI — Brain Module
Sends structured data to AI (Groq/DeepSeek/Gemini/Claude/Kimi) and parses trading decisions.
"""
import json
import time
from typing import Any, Dict, Optional

import httpx

from src.ai.prompts import SYSTEM_PROMPT, build_cycle_prompt
from src.utils.config import settings
from src.utils.logger import log


# AI Provider configs: {provider: {url, model_key, ...}}
AI_PROVIDERS = {
    "groq": {
        "url": "https://api.groq.com/openai/v1/chat/completions",
        "headers_fn": lambda key: {"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
    },
    "deepseek": {
        "url": "https://api.deepseek.com/v1/chat/completions",
        "headers_fn": lambda key: {"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
    },
    "gemini": {
        "url": "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions",
        "headers_fn": lambda key: {"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
    },
    "claude": {
        "url": "https://api.anthropic.com/v1/messages",
        "headers_fn": lambda key: {
            "x-api-key": key,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json",
        },
    },
    "kimi": {
        "url": "https://api.moonshot.cn/v1/chat/completions",
        "headers_fn": lambda key: {"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
    },
}


class AIBrain:
    """
    Sends cycle data to AI provider and returns parsed trading decisions.
    Supports: Groq, DeepSeek, Gemini, Claude, Kimi — configurable via .env
    """

    def __init__(self):
        self.provider = settings.AI_PROVIDER
        self.model = settings.AI_MODEL
        self.api_key = settings.AI_API_KEY

    async def decide(self, ai_input: dict) -> Dict[str, Any]:
        """
        Main entry point: send data to AI, get trading decisions.
        Returns: {"analysis": "...", "actions": [...], "meta": {...}}
        """
        prompt = build_cycle_prompt(ai_input)

        start_time = time.time()
        raw_response, usage = await self._call_ai(prompt)
        latency_ms = int((time.time() - start_time) * 1000)

        # Parse JSON from response
        parsed = self._parse_response(raw_response)

        # Add metadata
        parsed["meta"] = {
            "model": self.model,
            "provider": self.provider,
            "latency_ms": latency_ms,
            "prompt_tokens": usage.get("prompt_tokens", 0),
            "completion_tokens": usage.get("completion_tokens", 0),
            "cost_usd": self._estimate_cost(usage),
        }

        log.info(
            f"AI decision: {len(parsed.get('actions', []))} actions | "
            f"{latency_ms}ms | {self.provider}/{self.model}"
        )

        return parsed

    async def _call_ai(self, prompt: str) -> tuple:
        """Call AI provider API. Returns (response_text, usage_dict)."""
        provider_config = AI_PROVIDERS.get(self.provider)
        if not provider_config:
            log.error(f"Unknown AI provider: {self.provider}")
            return self._fallback_response(), {}

        try:
            if self.provider == "claude":
                return await self._call_claude(prompt)
            else:
                return await self._call_openai_compatible(prompt, provider_config)
        except Exception as e:
            log.error(f"AI call failed ({self.provider}): {e}")
            # Try fallback
            if settings.AI_FALLBACK_PROVIDER:
                log.info(f"Trying fallback: {settings.AI_FALLBACK_PROVIDER}")
                return await self._call_fallback(prompt)
            return self._fallback_response(), {}

    async def _call_openai_compatible(self, prompt: str, config: dict) -> tuple:
        """Call OpenAI-compatible API (Groq, DeepSeek, Gemini, Kimi)."""
        headers = config["headers_fn"](self.api_key)
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            "temperature": settings.AI_TEMPERATURE,
            "max_tokens": settings.AI_MAX_TOKENS,
            "response_format": {"type": "json_object"},
        }

        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(config["url"], json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()

        content = data.get("choices", [{}])[0].get("message", {}).get("content", "{}")
        usage = data.get("usage", {})
        return content, usage

    async def _call_claude(self, prompt: str) -> tuple:
        """Call Anthropic Claude API."""
        headers = AI_PROVIDERS["claude"]["headers_fn"](self.api_key)
        payload = {
            "model": self.model,
            "max_tokens": settings.AI_MAX_TOKENS,
            "system": SYSTEM_PROMPT,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": settings.AI_TEMPERATURE,
        }

        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(AI_PROVIDERS["claude"]["url"], json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()

        content = data.get("content", [{}])[0].get("text", "{}")
        usage = data.get("usage", {})
        # Map Claude usage keys to standard
        usage = {
            "prompt_tokens": usage.get("input_tokens", 0),
            "completion_tokens": usage.get("output_tokens", 0),
        }
        return content, usage

    async def _call_fallback(self, prompt: str) -> tuple:
        """Call fallback AI provider."""
        old_provider = self.provider
        old_model = self.model
        old_key = self.api_key

        self.provider = settings.AI_FALLBACK_PROVIDER
        self.model = settings.AI_FALLBACK_MODEL
        self.api_key = settings.AI_FALLBACK_API_KEY

        try:
            result = await self._call_ai(prompt)
            return result
        finally:
            self.provider = old_provider
            self.model = old_model
            self.api_key = old_key

    def _parse_response(self, raw: str) -> dict:
        """Parse AI response JSON, handling potential formatting issues."""
        try:
            # Try direct JSON parse
            parsed = json.loads(raw)
            if "actions" in parsed:
                return parsed
        except json.JSONDecodeError:
            pass

        # Try extracting JSON from markdown code blocks
        try:
            if "```json" in raw:
                json_str = raw.split("```json")[1].split("```")[0].strip()
                return json.loads(json_str)
            elif "```" in raw:
                json_str = raw.split("```")[1].split("```")[0].strip()
                return json.loads(json_str)
        except (json.JSONDecodeError, IndexError):
            pass

        # Try finding JSON object in text
        try:
            start = raw.index("{")
            end = raw.rindex("}") + 1
            return json.loads(raw[start:end])
        except (ValueError, json.JSONDecodeError):
            pass

        log.error(f"Failed to parse AI response: {raw[:200]}")
        return {"analysis": "Parse error", "actions": []}

    def _fallback_response(self) -> str:
        """Return a safe fallback if AI is completely unavailable."""
        return json.dumps({
            "analysis": "AI unavailable — HOLD all positions, skip new entries",
            "actions": [],
        })

    def _estimate_cost(self, usage: dict) -> float:
        """Estimate API cost in USD based on provider pricing."""
        prompt_tok = usage.get("prompt_tokens", 0)
        completion_tok = usage.get("completion_tokens", 0)

        # Pricing per million tokens
        pricing = {
            "groq": (0.59, 0.79),         # Llama 3.3 70B
            "deepseek": (0.28, 0.42),      # V3.2
            "gemini": (0.30, 2.50),        # 2.5 Flash
            "claude": (0.80, 4.00),        # Haiku 3.5
            "kimi": (0.60, 2.50),          # K2.5
        }

        input_price, output_price = pricing.get(self.provider, (1.0, 3.0))
        cost = (prompt_tok * input_price / 1_000_000) + (completion_tok * output_price / 1_000_000)
        return round(cost, 6)
