"""
ClawBot AI — Configuration Module
Pydantic-based settings loaded from .env file
"""
import os
from typing import List, Optional
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """All configuration loaded from environment variables."""

    # === Binance API ===
    BINANCE_API_KEY: str = ""
    BINANCE_API_SECRET: str = ""
    BINANCE_TESTNET: bool = True  # True = testnet, False = live

    # === AI Model ===
    AI_PROVIDER: str = "groq"  # groq / deepseek / gemini / claude / kimi
    AI_MODEL: str = "llama-3.3-70b-versatile"
    AI_API_KEY: str = ""
    AI_TEMPERATURE: float = 0.3
    AI_MAX_TOKENS: int = 2000

    # Fallback AI (optional)
    AI_FALLBACK_PROVIDER: str = ""
    AI_FALLBACK_MODEL: str = ""
    AI_FALLBACK_API_KEY: str = ""

    # === Trading ===
    LEVERAGE: int = 20
    TRADING_SYMBOLS: str = "BTCUSDT,ETHUSDT,SOLUSDT,BNBUSDT,XRPUSDT,DOGEUSDT,AVAXUSDT,LINKUSDT"
    MAX_POSITIONS: int = 5  # max concurrent positions (AI decides actual count)
    MIN_ORDER_USDT: float = 5.0

    # Safety SL/TP (fallback for between cycles)
    SAFETY_SL_PCT: float = 8.0   # -8% from entry
    SAFETY_TP_PCT: float = 15.0  # +15% from entry

    # === Risk tiers (balance-based) ===
    RISK_TIER_TINY: float = 20.0    # <$50 → 20% per trade
    RISK_TIER_SMALL: float = 10.0   # $50-100 → 10%
    RISK_TIER_MEDIUM: float = 7.0   # $100-300 → 7%
    RISK_TIER_LARGE: float = 4.0    # $300-1000 → 4%
    RISK_TIER_XL: float = 2.5       # >$1000 → 2.5%

    # === Timeframes ===
    TF_PRIMARY: str = "5m"
    TF_SECONDARY: str = "15m"
    TF_TERTIARY: str = "1h"
    CANDLES_PRIMARY: int = 200
    CANDLES_SECONDARY: int = 100
    CANDLES_TERTIARY: int = 48

    # === News ===
    CRYPTOPANIC_API_KEY: str = ""  # free tier key
    NEWS_COUNT: int = 20
    NEWS_TIMEOUT_SECONDS: int = 15

    # === Notifications ===
    TELEGRAM_BOT_TOKEN: str = ""
    TELEGRAM_CHAT_ID: str = ""
    DISCORD_WEBHOOK_URL: str = ""

    # === Database ===
    SUPABASE_URL: str = ""
    SUPABASE_KEY: str = ""

    # === Logging ===
    LOG_LEVEL: str = "INFO"
    LOG_FILE: str = "logs/clawbot.log"

    # === Binance API URLs ===
    @property
    def binance_base_url(self) -> str:
        if self.BINANCE_TESTNET:
            return "https://testnet.binancefuture.com"
        return "https://fapi.binance.com"

    @property
    def binance_ws_url(self) -> str:
        if self.BINANCE_TESTNET:
            return "wss://stream.binancefuture.com"
        return "wss://fstream.binance.com"

    @property
    def symbols_list(self) -> List[str]:
        return [s.strip() for s in self.TRADING_SYMBOLS.split(",") if s.strip()]

    def get_risk_pct(self, balance: float) -> float:
        """Dynamic risk % based on balance tier."""
        if balance < 50:
            return self.RISK_TIER_TINY
        elif balance < 100:
            return self.RISK_TIER_SMALL
        elif balance < 300:
            return self.RISK_TIER_MEDIUM
        elif balance < 1000:
            return self.RISK_TIER_LARGE
        else:
            return self.RISK_TIER_XL

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


# Singleton
settings = Settings()
