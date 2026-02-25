"""Base scorer abstract class."""
from abc import ABC, abstractmethod
import pandas as pd
import numpy as np
from common.logger import get_logger

class BaseScorer(ABC):
    def __init__(self):
        self.logger = get_logger(self.__class__.__name__)

    @abstractmethod
    def score(self, df: pd.DataFrame) -> float:
        """Return score in [-100, +100]."""
        pass

    def normalize_zscore(self, series: pd.Series, window: int = 20) -> float:
        """Normalize last value using rolling Z-score, clipped to [-100, +100]."""
        if len(series) < window:
            return 0.0
        rolling = series.rolling(window)
        mean = rolling.mean().iloc[-1]
        std = rolling.std().iloc[-1]
        if std == 0 or np.isnan(std):
            return 0.0
        z = (series.iloc[-1] - mean) / std
        return float(np.clip(z * 33, -100, 100))
