"""MOEX (Moscow Exchange) public API ingestor."""
import pandas as pd
import numpy as np
import requests
from datetime import datetime, timedelta
from ingest.base import BaseIngestor

class MOEXIngestor(BaseIngestor):
    BASE_URL = "https://iss.moex.com/iss/history/engines/stock/markets/shares/boards/TQBR/securities"

    def fetch(self, ticker: str, period: str = "3mo") -> pd.DataFrame:
        try:
            self.logger.info(f"Fetching {ticker} from MOEX...")
            end = datetime.now()
            start = end - timedelta(days=90)
            url = f"{self.BASE_URL}/{ticker}.json"
            params = {
                "from": start.strftime("%Y-%m-%d"),
                "till": end.strftime("%Y-%m-%d"),
                "iss.meta": "off",
            }
            resp = requests.get(url, params=params, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            cols = data["history"]["columns"]
            rows = data["history"]["data"]
            if not rows:
                raise ValueError("Empty MOEX response")
            df = pd.DataFrame(rows, columns=cols)
            df["TRADEDATE"] = pd.to_datetime(df["TRADEDATE"])
            df = df.set_index("TRADEDATE").sort_index()
            df = df.rename(columns={"OPEN": "open", "HIGH": "high", "LOW": "low",
                                     "CLOSE": "close", "VOLUME": "volume"})
            df = df[["open", "high", "low", "close", "volume"]].dropna()
            self.logger.info(f"Got {len(df)} rows for {ticker}")
            return df
        except Exception as e:
            self.logger.warning(f"MOEX failed for {ticker}: {e}. Using mock data.")
            return self._mock_data(ticker)

    def _mock_data(self, ticker: str) -> pd.DataFrame:
        dates = pd.date_range(end=pd.Timestamp.now(), periods=90, freq="D")
        np.random.seed(hash(ticker) % 2**32)
        price = 200 + np.cumsum(np.random.randn(90) * 5)
        price = np.abs(price)
        return pd.DataFrame({
            "open": price * (1 + np.random.randn(90) * 0.005),
            "high": price * (1 + np.abs(np.random.randn(90)) * 0.01),
            "low":  price * (1 - np.abs(np.random.randn(90)) * 0.01),
            "close": price,
            "volume": np.random.randint(100_000, 5_000_000, 90).astype(float),
        }, index=dates)
