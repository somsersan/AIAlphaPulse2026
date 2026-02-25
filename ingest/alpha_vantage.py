"""Alpha Vantage news & sentiment ingestor."""
import requests
import pandas as pd
from datetime import datetime
from ingest.base import BaseIngestor
import os

class AlphaVantageIngestor(BaseIngestor):
    BASE_URL = "https://www.alphavantage.co/query"

    def __init__(self):
        super().__init__()
        self.api_key = os.getenv("ALPHA_VANTAGE_API_KEY", "demo")

    def fetch(self, ticker: str, period: str = "3mo") -> pd.DataFrame:
        """Fetch OHLCV via Alpha Vantage (fallback to mock)."""
        try:
            params = {"function": "TIME_SERIES_DAILY", "symbol": ticker,
                      "outputsize": "compact", "apikey": self.api_key}
            resp = requests.get(self.BASE_URL, params=params, timeout=10)
            data = resp.json().get("Time Series (Daily)", {})
            if not data:
                raise ValueError("No data")
            rows = []
            for date_str, vals in data.items():
                rows.append({"timestamp": pd.to_datetime(date_str),
                    "open": float(vals["1. open"]), "high": float(vals["2. high"]),
                    "low": float(vals["3. low"]), "close": float(vals["4. close"]),
                    "volume": float(vals["5. volume"])})
            df = pd.DataFrame(rows).set_index("timestamp").sort_index()
            return df
        except Exception as e:
            self.logger.warning(f"Alpha Vantage OHLCV failed: {e}")
            return self._mock_data(ticker)

    def fetch_news(self, ticker: str, limit: int = 50) -> list[dict]:
        """Fetch news headlines for sentiment scoring."""
        try:
            params = {"function": "NEWS_SENTIMENT", "tickers": ticker,
                      "limit": limit, "apikey": self.api_key}
            resp = requests.get(self.BASE_URL, params=params, timeout=10)
            feed = resp.json().get("feed", [])
            return [{"title": a["title"], "summary": a.get("summary",""),
                     "published": a["time_published"],
                     "sentiment": float(a.get("overall_sentiment_score", 0))}
                    for a in feed]
        except Exception as e:
            self.logger.warning(f"Alpha Vantage news failed: {e}")
            return []

    def _mock_data(self, ticker: str):
        import numpy as np
        dates = pd.date_range(end=pd.Timestamp.now(), periods=90, freq="D")
        np.random.seed(hash(ticker) % 2**32)
        price = np.abs(100 + np.cumsum(np.random.randn(90) * 2))
        return pd.DataFrame({
            "open": price*(1+np.random.randn(90)*0.005),
            "high": price*(1+np.abs(np.random.randn(90))*0.01),
            "low":  price*(1-np.abs(np.random.randn(90))*0.01),
            "close": price, "volume": np.random.randint(1_000_000,50_000_000,90).astype(float),
        }, index=dates)
