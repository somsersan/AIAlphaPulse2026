"""Base ingestor abstract class."""
from abc import ABC, abstractmethod
import pandas as pd
from common.logger import get_logger

class BaseIngestor(ABC):
    def __init__(self):
        self.logger = get_logger(self.__class__.__name__)

    @abstractmethod
    def fetch(self, ticker: str, period: str = "3mo") -> pd.DataFrame:
        """Fetch OHLCV data. Returns DataFrame with columns: open, high, low, close, volume."""
        pass

    def validate(self, df: pd.DataFrame) -> bool:
        required = {"open", "high", "low", "close", "volume"}
        return not df.empty and required.issubset({c.lower() for c in df.columns})
