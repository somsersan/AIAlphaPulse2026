"""Aggregates all scorers into a single AI SCORE."""
import pandas as pd
import numpy as np
from datetime import datetime
from common.models import Asset, ScoringResult
from common.logger import get_logger
from scoring.trend import TrendScorer
from scoring.volatility import VolatilityScorer

logger = get_logger("aggregator")

WEIGHTS = {"trend": 0.6, "volatility": 0.4}

def signal_from_score(score: float) -> str:
    if score >= 60:  return "STRONG BUY"
    if score >= 25:  return "BUY"
    if score >= -25: return "NEUTRAL"
    if score >= -60: return "SELL"
    return "STRONG SELL"

def explain(trend: float, vol: float, ai: float) -> str:
    parts = []
    if trend > 30:   parts.append("сильный восходящий тренд")
    elif trend < -30: parts.append("нисходящий тренд")
    else:             parts.append("нейтральный тренд")
    if vol > 20:      parts.append("низкая волатильность ✅")
    elif vol < -20:   parts.append("высокая волатильность ⚠️")
    return "| ".join(parts) if parts else "нейтральный рынок"

def score_asset(asset: Asset, df: pd.DataFrame) -> ScoringResult:
    trend_score = TrendScorer().score(df)
    vol_score   = VolatilityScorer().score(df)
    ai_score    = trend_score * WEIGHTS["trend"] + vol_score * WEIGHTS["volatility"]
    ai_score    = float(np.clip(ai_score, -100, 100))
    return ScoringResult(
        asset=asset,
        timestamp=datetime.utcnow(),
        trend_score=round(trend_score, 1),
        volatility_score=round(vol_score, 1),
        ai_score=round(ai_score, 1),
        signal=signal_from_score(ai_score),
        explanation=explain(trend_score, vol_score, ai_score),
    )
