"""
Database storage layer.
Uses PostgreSQL if DATABASE_URL is set, otherwise saves to CSV files.
"""
import os
import pandas as pd
from pathlib import Path
from datetime import datetime
from common.logger import get_logger
from common.models import ScoringResult

logger = get_logger("database")
DATA_DIR = Path(__file__).parent.parent / "data"
DATA_DIR.mkdir(exist_ok=True)

def save_scores(results: list[ScoringResult]):
    """Save scoring results to CSV (PostgreSQL coming in Phase 3)."""
    rows = []
    for r in results:
        rows.append({
            "timestamp": r.timestamp.isoformat(),
            "ticker": r.asset.ticker,
            "asset_type": r.asset.asset_type,
            "trend_score": r.trend_score,
            "volatility_score": r.volatility_score,
            "ai_score": r.ai_score,
            "signal": r.signal,
            "explanation": r.explanation,
        })
    df = pd.DataFrame(rows)
    path = DATA_DIR / "scores.csv"
    if path.exists():
        existing = pd.read_csv(path)
        df = pd.concat([existing, df], ignore_index=True)
    df.to_csv(path, index=False)
    logger.info(f"Saved {len(rows)} scores to {path}")

def load_history(ticker: str, days: int = 30) -> pd.DataFrame:
    """Load score history for a ticker."""
    path = DATA_DIR / "scores.csv"
    if not path.exists():
        return pd.DataFrame()
    df = pd.read_csv(path)
    df = df[df["ticker"] == ticker.upper()]
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    cutoff = pd.Timestamp.now() - pd.Timedelta(days=days)
    return df[df["timestamp"] >= cutoff].sort_values("timestamp")

def load_latest_all() -> pd.DataFrame:
    """Load the latest score for each ticker."""
    path = DATA_DIR / "scores.csv"
    if not path.exists():
        return pd.DataFrame()
    df = pd.read_csv(path)
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    return df.sort_values("timestamp").groupby("ticker").last().reset_index()
