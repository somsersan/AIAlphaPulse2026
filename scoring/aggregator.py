"""Aggregates all scorers into a single AI SCORE (-100..+100)."""
import numpy as np
from datetime import datetime
from common.models import Asset, ScoringResult
from common.logger import get_logger
from scoring.trend import TrendScorer
from scoring.volatility import VolatilityScorer
from scoring.sentiment import SentimentScorer
from scoring.fundamental import FundamentalScorer
import pandas as pd

logger = get_logger("aggregator")

# Scoring weights (must sum to 1.0)
WEIGHTS = {
    "trend":       0.35,
    "volatility":  0.20,
    "sentiment":   0.25,
    "fundamental": 0.20,
}

def signal_from_score(score: float) -> str:
    if score >= 60:   return "STRONG BUY"
    if score >= 25:   return "BUY"
    if score >= -25:  return "NEUTRAL"
    if score >= -60:  return "SELL"
    return "STRONG SELL"

def build_explanation(t: float, v: float, s: float, f: float) -> str:
    parts = []
    if t > 30:    parts.append("📈 сильный тренд")
    elif t < -30: parts.append("📉 нисходящий тренд")
    if s > 30:    parts.append("😀 позитивный сентимент")
    elif s < -30: parts.append("😰 негативный сентимент")
    if v > 20:    parts.append("✅ низкая волатильность")
    elif v < -20: parts.append("⚠️ высокая волатильность")
    if f > 30:    parts.append("💰 сильный фундаментал")
    elif f < -30: parts.append("📉 слабый фундаментал")
    return " | ".join(parts) if parts else "нейтральный рынок"

def score_asset(asset: Asset, df: pd.DataFrame,
                news: list[dict] | None = None) -> ScoringResult:
    t = TrendScorer().score(df)
    v = VolatilityScorer().score(df)
    s = SentimentScorer().score(df, news=news)
    f = FundamentalScorer().score(df, ticker=asset.ticker if asset.asset_type == "stock" else None)

    ai = (t * WEIGHTS["trend"] + v * WEIGHTS["volatility"] +
          s * WEIGHTS["sentiment"] + f * WEIGHTS["fundamental"])
    ai = float(np.clip(ai, -100, 100))

    return ScoringResult(
        asset=asset, timestamp=datetime.utcnow(),
        trend_score=round(t, 1), volatility_score=round(v, 1),
        ai_score=round(ai, 1), signal=signal_from_score(ai),
        explanation=build_explanation(t, v, s, f),
    )
