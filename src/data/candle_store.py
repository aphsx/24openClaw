"""
ClawBot AI — Candle Store
Multi-timeframe candlestick data management.
Converts raw Binance klines into pandas DataFrames.
"""
import pandas as pd
from typing import Dict, List, Optional

from src.utils.logger import log


class CandleStore:
    """
    Manages candlestick data for multiple symbols and timeframes.
    Stores as pandas DataFrames in memory for fast indicator calculation.
    """

    def __init__(self):
        # {symbol: {tf: DataFrame}}
        self._candles: Dict[str, Dict[str, pd.DataFrame]] = {}

    def store(self, symbol: str, timeframe: str, raw_klines: List[list]):
        """
        Convert raw Binance klines to DataFrame and store.
        
        Binance kline format:
        [open_time, open, high, low, close, volume, close_time,
         quote_volume, trades, taker_buy_vol, taker_buy_quote_vol, ignore]
        """
        if not raw_klines:
            log.warning(f"No klines for {symbol} {timeframe}")
            return

        df = pd.DataFrame(raw_klines, columns=[
            "open_time", "open", "high", "low", "close", "volume",
            "close_time", "quote_volume", "trades", "taker_buy_volume",
            "taker_buy_quote_volume", "ignore",
        ])

        # Convert types
        for col in ["open", "high", "low", "close", "volume", "quote_volume",
                     "taker_buy_volume", "taker_buy_quote_volume"]:
            df[col] = pd.to_numeric(df[col], errors="coerce")

        df["open_time"] = pd.to_datetime(df["open_time"], unit="ms")
        df["close_time"] = pd.to_datetime(df["close_time"], unit="ms")
        df["trades"] = df["trades"].astype(int)

        # Sort by time
        df = df.sort_values("open_time").reset_index(drop=True)

        if symbol not in self._candles:
            self._candles[symbol] = {}
        self._candles[symbol][timeframe] = df

    def get(self, symbol: str, timeframe: str) -> Optional[pd.DataFrame]:
        """Get DataFrame for symbol/timeframe."""
        return self._candles.get(symbol, {}).get(timeframe)

    def get_latest_price(self, symbol: str) -> float:
        """Get latest close price from 5m candles."""
        df = self.get(symbol, "5m")
        if df is not None and len(df) > 0:
            return float(df["close"].iloc[-1])
        return 0.0

    def get_all_symbols(self) -> List[str]:
        """Get list of all stored symbols."""
        return list(self._candles.keys())

    def refresh_latest(self, symbol: str, timeframe: str, raw_klines: List[list]):
        """
        Refresh with latest data — replace old candles.
        Used when news fetch was slow and we need fresh chart data.
        """
        self.store(symbol, timeframe, raw_klines)
        log.debug(f"Refreshed {symbol} {timeframe} candles")
