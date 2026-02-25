"""
Sentiment Scorer.

Оценивает рыночный сентимент по нескольким источникам:
1. Alpha Vantage News Sentiment API (если есть ключ)
2. RSI divergence — технический прокси сентимента
3. Price/Volume divergence — смарт-мани vs толпа
4. Momentum oscillator — скорость изменения цены

Формулы:
  - CCI (Commodity Channel Index) — отклонение от средней цены
  - Williams %R — моментум осциллятор
  - Volume-price trend (VPT)
"""
import numpy as np
import pandas as pd
from scoring.base import BaseScorer
import os


class SentimentScorer(BaseScorer):

    def score(self, df: pd.DataFrame,
              news: list[dict] | None = None,
              ticker: str | None = None) -> float:
        try:
            scores = []

            # 1. Новостной сентимент через Alpha Vantage
            if ticker and os.getenv("ALPHA_VANTAGE_API_KEY"):
                news_score = self._news_sentiment(ticker)
                if news_score is not None:
                    scores.append((news_score, 0.4))

            # 2. Переданные новости (если есть)
            if news:
                raw = np.mean([float(n.get("sentiment", 0)) for n in news])
                scores.append((float(np.clip(raw * 100, -100, 100)), 0.4))

            # 3. CCI (Commodity Channel Index) — отклонение типичной цены
            cci_score = self._cci_score(df)
            scores.append((cci_score, 0.25))

            # 4. Williams %R — перекупленность/перепроданность
            wr_score = self._williams_r_score(df)
            scores.append((wr_score, 0.20))

            # 5. Volume-Price Trend (VPT)
            vpt_score = self._vpt_score(df)
            scores.append((vpt_score, 0.15))

            if not scores:
                return 0.0

            total_w = sum(w for _, w in scores)
            result  = sum(s * w for s, w in scores) / total_w
            return float(np.clip(result, -100, 100))

        except Exception as e:
            self.logger.error(f"SentimentScorer error: {e}")
            return 0.0

    def _news_sentiment(self, ticker: str) -> float | None:
        try:
            import requests
            api_key = os.getenv("ALPHA_VANTAGE_API_KEY", "demo")
            resp = requests.get(
                "https://www.alphavantage.co/query",
                params={"function": "NEWS_SENTIMENT", "tickers": ticker,
                        "limit": 50, "apikey": api_key},
                timeout=8
            )
            feed = resp.json().get("feed", [])
            if not feed:
                return None
            sentiments = []
            for article in feed[:20]:
                for ts in article.get("ticker_sentiment", []):
                    if ts["ticker"] == ticker:
                        sentiments.append(float(ts.get("ticker_sentiment_score", 0)))
            if sentiments:
                return float(np.clip(np.mean(sentiments) * 100, -100, 100))
        except Exception as e:
            self.logger.warning(f"News sentiment failed for {ticker}: {e}")
        return None

    def _cci_score(self, df: pd.DataFrame, period: int = 20) -> float:
        """
        CCI = (Typical Price - MA) / (0.015 * Mean Deviation)
        Typical Price = (High + Low + Close) / 3

        CCI > 100: перекупленность (может быть + в momentum стратегии)
        CCI < -100: перепроданность
        """
        high  = df["high"].astype(float)
        low   = df["low"].astype(float)
        close = df["close"].astype(float)
        if len(close) < period:
            return 0.0

        tp  = (high + low + close) / 3
        ma  = tp.rolling(period).mean()
        mad = tp.rolling(period).apply(lambda x: np.abs(x - x.mean()).mean())

        cci = (tp - ma) / (0.015 * mad + 1e-10)
        current_cci = cci.iloc[-1]

        # Нормализуем: CCI ±200 → ±100 score
        return float(np.clip(current_cci / 2, -100, 100))

    def _williams_r_score(self, df: pd.DataFrame, period: int = 14) -> float:
        """
        Williams %R = (Highest High - Close) / (Highest High - Lowest Low) * -100

        %R от 0 до -20: перекупленность → осторожно
        %R от -80 до -100: перепроданность → потенциал отскока
        """
        high  = df["high"].astype(float)
        low   = df["low"].astype(float)
        close = df["close"].astype(float)
        if len(close) < period:
            return 0.0

        hh = high.rolling(period).max()
        ll = low.rolling(period).min()

        wr = (hh - close) / (hh - ll + 1e-10) * -100
        current_wr = wr.iloc[-1]

        # Инвертируем: -80 до -100 = перепроданность = потенциал роста = +score
        # Используем как momentum: если выходим из oversold → bullish
        wr_trend = wr.iloc[-1] - wr.iloc[-5]  # растёт из oversold = хорошо
        if current_wr < -80:
            base = 60.0   # oversold — ждём отскока
        elif current_wr < -50:
            base = 10.0   # нейтрально
        elif current_wr < -20:
            base = -10.0
        else:
            base = -40.0  # overbought

        trend_adj = float(np.clip(wr_trend * 2, -30, 30))
        return float(np.clip(base + trend_adj, -100, 100))

    def _vpt_score(self, df: pd.DataFrame) -> float:
        """
        Volume Price Trend (VPT):
        VPT[i] = VPT[i-1] + Volume[i] * (Close[i] - Close[i-1]) / Close[i-1]

        Z-score VPT тренда → кто покупает с объёмом.
        """
        close  = df["close"].astype(float)
        volume = df["volume"].astype(float)
        if len(close) < 20:
            return 0.0

        returns = close.pct_change().fillna(0)
        vpt     = (volume * returns).cumsum()
        return self.normalize_zscore(vpt, window=20)
