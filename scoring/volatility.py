"""Volatility scorer: ATR + Bollinger Bands."""
import pandas as pd
import numpy as np
from scoring.base import BaseScorer

class VolatilityScorer(BaseScorer):
    def score(self, df: pd.DataFrame) -> float:
        try:
            close = df["close"].astype(float)
            high  = df["high"].astype(float)
            low   = df["low"].astype(float)
            if len(close) < 20:
                return 0.0

            # ATR (14)
            tr = pd.concat([
                high - low,
                (high - close.shift()).abs(),
                (low  - close.shift()).abs(),
            ], axis=1).max(axis=1)
            atr = tr.rolling(14).mean()
            atr_pct = atr / close  # normalized ATR as % of price
            atr_z = self.normalize_zscore(atr_pct)

            # Bollinger Bands width
            ma20 = close.rolling(20).mean()
            std20 = close.rolling(20).std()
            bb_width = (2 * std20) / ma20
            bb_z = self.normalize_zscore(bb_width)

            # Low volatility in context of uptrend = positive score
            # High volatility = risk = negative score
            raw = -(atr_z * 0.5 + bb_z * 0.5)
            return float(np.clip(raw, -100, 100))
        except Exception as e:
            self.logger.error(f"VolatilityScorer error: {e}")
            return 0.0
