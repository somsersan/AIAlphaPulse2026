"""Yahoo Finance ingestor via yfinance."""
import pandas as pd
import numpy as np
from ingest.base import BaseIngestor

class YahooFinanceIngestor(BaseIngestor):
    def fetch(self, ticker: str, period: str = "3mo") -> pd.DataFrame:
        try:
            import yfinance as yf
            self.logger.info(f"Fetching {ticker} from Yahoo Finance...")
            df = yf.download(ticker, period=period, progress=False, auto_adjust=True)
            if df.empty:
                raise ValueError("Empty response")
            df.columns = [c.lower() for c in df.columns]
            df = df[["open", "high", "low", "close", "volume"]].dropna()
            self.logger.info(f"Got {len(df)} rows for {ticker}")
            return df
        except Exception as e:
            self.logger.warning(f"Yahoo Finance failed for {ticker}: {e}. Using mock data.")
            return self._mock_data(ticker)

    def _mock_data(self, ticker: str) -> pd.DataFrame:
        """Generate realistic mock OHLCV data as fallback."""
        dates = pd.date_range(end=pd.Timestamp.now(), periods=90, freq="D")
        np.random.seed(hash(ticker) % 2**32)
        price = 100 + np.cumsum(np.random.randn(90) * 2)
        price = np.abs(price)
        return pd.DataFrame({
            "open": price * (1 + np.random.randn(90) * 0.005),
            "high": price * (1 + np.abs(np.random.randn(90)) * 0.01),
            "low": price * (1 - np.abs(np.random.randn(90)) * 0.01),
            "close": price,
            "volume": np.random.randint(1_000_000, 50_000_000, 90).astype(float),
        }, index=dates)
