"""Binance public API ingestor (no API key required)."""
import pandas as pd
import numpy as np
import requests
from ingest.base import BaseIngestor

BINANCE_KLINES_URL = "https://api.binance.com/api/v3/klines"

class BinanceIngestor(BaseIngestor):
    def fetch(self, ticker: str, period: str = "3mo") -> pd.DataFrame:
        try:
            self.logger.info(f"Fetching {ticker} from Binance...")
            params = {"symbol": ticker.upper(), "interval": "1d", "limit": 90}
            resp = requests.get(BINANCE_KLINES_URL, params=params, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            if not data:
                raise ValueError("Empty response")
            df = pd.DataFrame(data, columns=[
                "timestamp", "open", "high", "low", "close", "volume",
                "close_time", "quote_volume", "trades", "taker_base", "taker_quote", "ignore"
            ])
            df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
            df = df.set_index("timestamp")
            for col in ["open", "high", "low", "close", "volume"]:
                df[col] = df[col].astype(float)
            self.logger.info(f"Got {len(df)} rows for {ticker}")
            return df[["open", "high", "low", "close", "volume"]]
        except Exception as e:
            self.logger.warning(f"Binance failed for {ticker}: {e}. Using mock data.")
            return self._mock_data(ticker)

    def _mock_data(self, ticker: str) -> pd.DataFrame:
        dates = pd.date_range(end=pd.Timestamp.now(), periods=90, freq="D")
        np.random.seed(hash(ticker) % 2**32)
        base = 40000 if "BTC" in ticker else 2000
        price = base + np.cumsum(np.random.randn(90) * base * 0.02)
        price = np.abs(price)
        return pd.DataFrame({
            "open": price * (1 + np.random.randn(90) * 0.005),
            "high": price * (1 + np.abs(np.random.randn(90)) * 0.015),
            "low":  price * (1 - np.abs(np.random.randn(90)) * 0.015),
            "close": price,
            "volume": np.random.rand(90) * 1000,
        }, index=dates)
