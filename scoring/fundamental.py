"""
Fundamental scorer.
Fetches P/E, ROE, Revenue Growth, Debt/Equity via yfinance.
Score range: -100 to +100
"""
import numpy as np
from scoring.base import BaseScorer
import pandas as pd

class FundamentalScorer(BaseScorer):
    def score(self, df: pd.DataFrame, ticker: str | None = None) -> float:
        if ticker:
            try:
                return self._score_from_fundamentals(ticker)
            except Exception as e:
                self.logger.warning(f"Fundamental fetch failed for {ticker}: {e}")
        return self._score_from_price_momentum(df)

    def _score_from_fundamentals(self, ticker: str) -> float:
        import yfinance as yf
        info = yf.Ticker(ticker).info
        score = 0.0
        weight_total = 0.0

        # P/E ratio (lower = better for value, 10-20 ideal)
        pe = info.get("trailingPE")
        if pe and pe > 0:
            if pe < 15:    pe_score = 70.0
            elif pe < 25:  pe_score = 30.0
            elif pe < 40:  pe_score = -10.0
            else:          pe_score = -50.0
            score += pe_score * 0.3
            weight_total += 0.3

        # ROE (Return on Equity, higher = better)
        roe = info.get("returnOnEquity")
        if roe is not None:
            roe_score = float(np.clip(roe * 200, -100, 100))
            score += roe_score * 0.3
            weight_total += 0.3

        # Revenue growth
        rev_growth = info.get("revenueGrowth")
        if rev_growth is not None:
            rg_score = float(np.clip(rev_growth * 200, -100, 100))
            score += rg_score * 0.2
            weight_total += 0.2

        # Debt/Equity (lower = better)
        de = info.get("debtToEquity")
        if de is not None:
            de_score = float(np.clip(-de / 2 + 50, -100, 100))
            score += de_score * 0.2
            weight_total += 0.2

        if weight_total == 0:
            return 0.0
        return float(np.clip(score / weight_total, -100, 100))

    def _score_from_price_momentum(self, df: pd.DataFrame) -> float:
        """Fallback: use long-term price momentum as proxy."""
        try:
            close = df["close"].astype(float)
            if len(close) < 60:
                return 0.0
            ret_60 = (close.iloc[-1] / close.iloc[-60] - 1) * 100
            return float(np.clip(ret_60 * 2, -100, 100))
        except:
            return 0.0
