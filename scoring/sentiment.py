"""
Sentiment scorer.
Uses Alpha Vantage news sentiment if available, otherwise TextBlob on headlines.
Score range: -100 (very negative) to +100 (very positive)
"""
import numpy as np
from scoring.base import BaseScorer
import pandas as pd

class SentimentScorer(BaseScorer):
    def score(self, df: pd.DataFrame, news: list[dict] | None = None) -> float:
        try:
            if news:
                return self._score_from_news(news)
            return self._score_from_price_action(df)
        except Exception as e:
            self.logger.error(f"SentimentScorer error: {e}")
            return 0.0

    def _score_from_news(self, news: list[dict]) -> float:
        if not news:
            return 0.0
        sentiments = [float(n.get("sentiment", 0)) for n in news]
        avg = np.mean(sentiments)
        # Alpha Vantage sentiment is -1..+1, scale to -100..+100
        return float(np.clip(avg * 100, -100, 100))

    def _score_from_price_action(self, df: pd.DataFrame) -> float:
        """Proxy sentiment via volume + price momentum."""
        try:
            close = df["close"].astype(float)
            volume = df["volume"].astype(float)
            if len(close) < 10:
                return 0.0
            # Volume-weighted price change over last 5 days
            recent_ret = close.pct_change(5).iloc[-1]
            vol_ratio = volume.iloc[-5:].mean() / (volume.iloc[-20:-5].mean() + 1e-10)
            # High volume + positive return = bullish sentiment
            raw = recent_ret * 100 * min(vol_ratio, 2.0)
            return float(np.clip(raw * 10, -100, 100))
        except:
            return 0.0
