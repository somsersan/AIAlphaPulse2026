"""Trend scorer: MA crossover + RSI."""
import pandas as pd
import numpy as np
from scoring.base import BaseScorer

class TrendScorer(BaseScorer):
    def score(self, df: pd.DataFrame) -> float:
        try:
            close = df["close"].astype(float)
            if len(close) < 50:
                return 0.0

            ma20 = close.rolling(20).mean()
            ma50 = close.rolling(50).mean()

            # MA crossover signal [-1, +1]
            ma_signal = 1.0 if ma20.iloc[-1] > ma50.iloc[-1] else -1.0
            ma_strength = abs(ma20.iloc[-1] - ma50.iloc[-1]) / ma50.iloc[-1]
            ma_score = ma_signal * min(ma_strength * 1000, 1.0)

            # RSI
            delta = close.diff()
            gain = delta.clip(lower=0).rolling(14).mean()
            loss = (-delta.clip(upper=0)).rolling(14).mean()
            rs = gain / (loss + 1e-10)
            rsi = 100 - (100 / (1 + rs))
            rsi_val = rsi.iloc[-1]

            # RSI score: 40-60 neutral, <30 oversold=bullish, >70 overbought=bearish
            if rsi_val < 30:
                rsi_score = 0.8
            elif rsi_val < 50:
                rsi_score = 0.3
            elif rsi_val < 70:
                rsi_score = -0.1
            else:
                rsi_score = -0.7

            # Z-score on price momentum
            momentum = close.pct_change(5)
            z_score = self.normalize_zscore(momentum) / 100

            combined = (ma_score * 0.4 + rsi_score * 0.3 + z_score * 0.3)
            return float(np.clip(combined * 100, -100, 100))
        except Exception as e:
            self.logger.error(f"TrendScorer error: {e}")
            return 0.0
