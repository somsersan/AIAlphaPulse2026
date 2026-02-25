"""
AI ALPHA PULSE — Master Aggregator

Объединяет 7 скоринг-агентов в единый AI SCORE (-100..+100).

Веса:
  Trend            35% — главный сигнал направления
  Sentiment        20% — настроение рынка
  Fundamental      20% — качество бизнеса (акции) / network value (крипто)
  Relative Strength 10% — сила относительно рынка
  Volatility        5% — контекст риска
  Insider/Funds     5% — институциональный интерес
  Macro             5% — макроэкономический фон

Итоговый AI SCORE = взвешенная сумма всех 7 компонентов.
"""
import numpy as np
from datetime import datetime
from common.models import Asset, ScoringResult
from common.logger import get_logger
from scoring.trend import TrendScorer
from scoring.volatility import VolatilityScorer
from scoring.sentiment import SentimentScorer
from scoring.fundamental import FundamentalScorer
from scoring.relative_strength import RelativeStrengthScorer
from scoring.insider_funds import InsiderFundsScorer
from scoring.macro import MacroScorer
import pandas as pd

logger = get_logger("aggregator")

WEIGHTS = {
    "trend":             0.35,
    "sentiment":         0.20,
    "fundamental":       0.20,
    "relative_strength": 0.10,
    "volatility":        0.05,
    "insider_funds":     0.05,
    "macro":             0.05,
}

assert abs(sum(WEIGHTS.values()) - 1.0) < 0.001, "Weights must sum to 1.0"


def signal_from_score(score: float) -> str:
    if score >= 60:   return "STRONG BUY"
    if score >= 25:   return "BUY"
    if score >= -25:  return "NEUTRAL"
    if score >= -60:  return "SELL"
    return "STRONG SELL"


def build_explanation(scores: dict[str, float]) -> str:
    parts = []
    t = scores.get("trend", 0)
    s = scores.get("sentiment", 0)
    f = scores.get("fundamental", 0)
    v = scores.get("volatility", 0)
    m = scores.get("macro", 0)
    rs = scores.get("relative_strength", 0)
    ins = scores.get("insider_funds", 0)

    if t > 40:    parts.append("📈 сильный тренд")
    elif t < -40: parts.append("📉 нисходящий тренд")
    if s > 30:    parts.append("😀 позитивный сентимент")
    elif s < -30: parts.append("😰 негативный сентимент")
    if f > 40:    parts.append("💰 сильный фундаментал")
    elif f < -40: parts.append("⚠️ слабый фундаментал")
    if rs > 30:   parts.append("💪 сильнее рынка")
    elif rs < -30: parts.append("😴 слабее рынка")
    if v > 30:    parts.append("✅ низкая волатильность")
    elif v < -30: parts.append("🌪 высокая волатильность")
    if ins > 30:  parts.append("🏦 институционалы покупают")
    if m > 30:    parts.append("🌍 позитивный макрофон")
    elif m < -30: parts.append("🌧 негативный макрофон")

    return " | ".join(parts) if parts else "🟡 нейтральный рынок"


def score_asset(asset: Asset, df: pd.DataFrame,
                news: list[dict] | None = None,
                benchmark_df: pd.DataFrame | None = None) -> ScoringResult:
    """
    Главная функция скоринга актива.
    Запускает все 7 агентов и агрегирует результат.
    """
    ticker = asset.ticker
    atype  = asset.asset_type

    logger.info(f"Scoring {ticker} ({atype})...")

    # Запускаем все 7 агентов
    factor_scores = {}

    try:
        factor_scores["trend"] = TrendScorer().score(df)
    except Exception as e:
        logger.error(f"Trend failed: {e}"); factor_scores["trend"] = 0.0

    try:
        factor_scores["volatility"] = VolatilityScorer().score(df)
    except Exception as e:
        logger.error(f"Volatility failed: {e}"); factor_scores["volatility"] = 0.0

    try:
        factor_scores["sentiment"] = SentimentScorer().score(df, news=news, ticker=ticker)
    except Exception as e:
        logger.error(f"Sentiment failed: {e}"); factor_scores["sentiment"] = 0.0

    try:
        factor_scores["fundamental"] = FundamentalScorer().score(df, ticker=ticker, asset_type=atype)
    except Exception as e:
        logger.error(f"Fundamental failed: {e}"); factor_scores["fundamental"] = 0.0

    try:
        factor_scores["relative_strength"] = RelativeStrengthScorer().score(
            df, benchmark_df=benchmark_df, asset_type=atype)
    except Exception as e:
        logger.error(f"RelativeStrength failed: {e}"); factor_scores["relative_strength"] = 0.0

    try:
        factor_scores["insider_funds"] = InsiderFundsScorer().score(df, ticker=ticker)
    except Exception as e:
        logger.error(f"InsiderFunds failed: {e}"); factor_scores["insider_funds"] = 0.0

    try:
        factor_scores["macro"] = MacroScorer().score(df, asset_type=atype)
    except Exception as e:
        logger.error(f"Macro failed: {e}"); factor_scores["macro"] = 0.0

    # Считаем AI SCORE
    ai_score = sum(factor_scores[k] * WEIGHTS[k] for k in WEIGHTS)
    ai_score = float(np.clip(ai_score, -100, 100))

    logger.info(f"{ticker} scores: {', '.join(f'{k}={v:.1f}' for k,v in factor_scores.items())}")
    logger.info(f"{ticker} AI SCORE = {ai_score:.1f} → {signal_from_score(ai_score)}")

    return ScoringResult(
        asset=asset,
        timestamp=datetime.utcnow(),
        trend_score=round(factor_scores["trend"], 1),
        volatility_score=round(factor_scores["volatility"], 1),
        ai_score=round(ai_score, 1),
        signal=signal_from_score(ai_score),
        explanation=build_explanation(factor_scores),
        # Дополнительные поля для детальной карточки
        factor_scores={k: round(v, 1) for k, v in factor_scores.items()},
        weights=WEIGHTS,
    )
