"""Database storage layer.

Backend is selected at startup via the DATABASE_URL environment variable:
  - DATABASE_URL=none (or unset) → CSV files in data/scores.csv (default / fallback)
  - DATABASE_URL=postgresql://... → PostgreSQL via SQLAlchemy async + asyncpg

All public functions are async so they integrate seamlessly with FastAPI.
"""
import asyncio
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

import pandas as pd

from common.logger import get_logger
from common.models import ScoringResult

logger = get_logger("database")

DATA_DIR = Path(__file__).parent.parent / "data"
DATA_DIR.mkdir(exist_ok=True)

# ── Backend detection ──────────────────────────────────────────────────────────
_raw_url: str = os.getenv("DATABASE_URL", "none").strip()
USE_POSTGRES: bool = _raw_url.lower() not in ("none", "", "null")

# PostgreSQL objects — populated only when USE_POSTGRES is True
_engine = None
_SessionFactory = None

if USE_POSTGRES:
    from sqlalchemy.dialects.postgresql import insert as pg_insert
    from sqlalchemy.ext.asyncio import (
        AsyncSession,
        async_sessionmaker,
        create_async_engine,
    )
    from sqlalchemy import func as sqlfunc, select
    from storage.models import AssetDB, Base, ScoringResultDB

    # Normalise URL scheme for asyncpg driver
    _db_url = _raw_url
    if _db_url.startswith("postgres://"):
        _db_url = "postgresql+asyncpg://" + _db_url[len("postgres://"):]
    elif _db_url.startswith("postgresql://") and "+asyncpg" not in _db_url:
        _db_url = _db_url.replace("postgresql://", "postgresql+asyncpg://", 1)

    _engine = create_async_engine(
        _db_url,
        echo=False,
        pool_pre_ping=True,
        pool_size=5,
        max_overflow=10,
    )
    _SessionFactory = async_sessionmaker(_engine, expire_on_commit=False)
    logger.info(f"[PG] Backend: {_db_url.split('@')[-1]}")
else:
    logger.info("[CSV] Backend: %s/scores.csv", DATA_DIR)


# ── CSV helpers (sync; run via asyncio.to_thread) ─────────────────────────────

def _csv_save_scores(results: list[ScoringResult], data_dir: Path) -> None:
    rows = []
    for r in results:
        fs = r.factor_scores
        rows.append({
            "timestamp": r.timestamp.isoformat(),
            "ticker": r.asset.ticker,
            "asset_type": r.asset.asset_type,
            "exchange": r.asset.exchange,
            "trend_score": r.trend_score,
            "volatility_score": r.volatility_score,
            "sentiment_score": fs.get("sentiment"),
            "fundamental_score": fs.get("fundamental"),
            "relative_strength_score": fs.get("relative_strength"),
            "insider_funds_score": fs.get("insider_funds"),
            "macro_score": fs.get("macro"),
            "ai_score": r.ai_score,
            "signal": r.signal,
            "explanation": r.explanation,
        })
    df = pd.DataFrame(rows)
    path = data_dir / "scores.csv"
    if path.exists():
        existing = pd.read_csv(path)
        df = pd.concat([existing, df], ignore_index=True)
    df.to_csv(path, index=False)
    logger.info("[CSV] Saved %d scores → %s", len(rows), path)


def _csv_load_history(ticker: str, days: int, data_dir: Path) -> pd.DataFrame:
    path = data_dir / "scores.csv"
    if not path.exists():
        return pd.DataFrame()
    df = pd.read_csv(path)
    df = df[df["ticker"] == ticker.upper()]
    if df.empty:
        return df
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
    cutoff = pd.Timestamp.now(tz="UTC") - pd.Timedelta(days=days)
    return df[df["timestamp"] >= cutoff].sort_values("timestamp")


def _csv_load_latest_all(data_dir: Path) -> pd.DataFrame:
    path = data_dir / "scores.csv"
    if not path.exists():
        return pd.DataFrame()
    df = pd.read_csv(path)
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    return df.sort_values("timestamp").groupby("ticker").last().reset_index()


# ── PostgreSQL helpers (async) ─────────────────────────────────────────────────

async def _pg_get_or_create_asset(session: "AsyncSession", r: ScoringResult) -> int:
    """Upsert asset row and return its id."""
    stmt = (
        pg_insert(AssetDB)
        .values(
            ticker=r.asset.ticker,
            name=r.asset.name,
            asset_type=r.asset.asset_type,
            exchange=r.asset.exchange,
        )
        .on_conflict_do_update(
            index_elements=["ticker"],
            set_={"name": r.asset.name, "exchange": r.asset.exchange},
        )
        .returning(AssetDB.id)
    )
    result = await session.execute(stmt)
    return result.scalar_one()


async def _pg_save_scores(results: list[ScoringResult]) -> None:
    async with _SessionFactory() as session:
        async with session.begin():
            for r in results:
                asset_id = await _pg_get_or_create_asset(session, r)
                fs = r.factor_scores
                stmt = (
                    pg_insert(ScoringResultDB)
                    .values(
                        asset_id=asset_id,
                        timestamp=r.timestamp,
                        trend_score=r.trend_score,
                        volatility_score=r.volatility_score,
                        sentiment_score=fs.get("sentiment"),
                        fundamental_score=fs.get("fundamental"),
                        relative_strength_score=fs.get("relative_strength"),
                        insider_funds_score=fs.get("insider_funds"),
                        macro_score=fs.get("macro"),
                        ai_score=r.ai_score,
                        signal=r.signal,
                        explanation=r.explanation,
                    )
                    .on_conflict_do_update(
                        index_elements=["asset_id", "timestamp"],
                        set_={
                            "ai_score": r.ai_score,
                            "signal": r.signal,
                            "explanation": r.explanation,
                        },
                    )
                )
                await session.execute(stmt)
    logger.info("[PG] Saved %d scores", len(results))


def _to_float(val) -> Optional[float]:
    return float(val) if val is not None else None


def _pg_row_to_dict(r: "ScoringResultDB", ticker: str, asset_type: str, exchange: str) -> dict:
    return {
        "timestamp": r.timestamp,
        "ticker": ticker,
        "asset_type": asset_type,
        "exchange": exchange,
        "trend_score": _to_float(r.trend_score),
        "volatility_score": _to_float(r.volatility_score),
        "sentiment_score": _to_float(r.sentiment_score),
        "fundamental_score": _to_float(r.fundamental_score),
        "relative_strength_score": _to_float(r.relative_strength_score),
        "insider_funds_score": _to_float(r.insider_funds_score),
        "macro_score": _to_float(r.macro_score),
        "ai_score": _to_float(r.ai_score),
        "signal": r.signal,
        "explanation": r.explanation,
    }


async def _pg_load_history(ticker: str, days: int) -> pd.DataFrame:
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    async with _SessionFactory() as session:
        stmt = (
            select(ScoringResultDB, AssetDB.ticker, AssetDB.asset_type, AssetDB.exchange)
            .join(AssetDB, ScoringResultDB.asset_id == AssetDB.id)
            .where(AssetDB.ticker == ticker.upper())
            .where(ScoringResultDB.timestamp >= cutoff)
            .order_by(ScoringResultDB.timestamp)
        )
        rows = (await session.execute(stmt)).all()
    if not rows:
        return pd.DataFrame()
    return pd.DataFrame([_pg_row_to_dict(r, t, at, ex) for r, t, at, ex in rows])


async def _pg_load_latest_all() -> pd.DataFrame:
    async with _SessionFactory() as session:
        subq = (
            select(
                ScoringResultDB.asset_id,
                sqlfunc.max(ScoringResultDB.timestamp).label("max_ts"),
            )
            .group_by(ScoringResultDB.asset_id)
            .subquery()
        )
        stmt = (
            select(ScoringResultDB, AssetDB.ticker, AssetDB.asset_type, AssetDB.exchange)
            .join(AssetDB, ScoringResultDB.asset_id == AssetDB.id)
            .join(
                subq,
                (ScoringResultDB.asset_id == subq.c.asset_id)
                & (ScoringResultDB.timestamp == subq.c.max_ts),
            )
        )
        rows = (await session.execute(stmt)).all()
    if not rows:
        return pd.DataFrame()
    return pd.DataFrame([_pg_row_to_dict(r, t, at, ex) for r, t, at, ex in rows])


# ── Public async API ───────────────────────────────────────────────────────────

async def save_scores(results: list[ScoringResult]) -> None:
    """Persist scoring results to PostgreSQL or CSV (based on DATABASE_URL)."""
    if not results:
        return
    if USE_POSTGRES:
        await _pg_save_scores(results)
    else:
        await asyncio.to_thread(_csv_save_scores, results, DATA_DIR)


async def load_history(ticker: str, days: int = 30) -> pd.DataFrame:
    """Return score history for *ticker* over the last *days* days."""
    if USE_POSTGRES:
        return await _pg_load_history(ticker, days)
    return await asyncio.to_thread(_csv_load_history, ticker, days, DATA_DIR)


async def load_latest_all() -> pd.DataFrame:
    """Return the most-recent score row for every tracked asset."""
    if USE_POSTGRES:
        return await _pg_load_latest_all()
    return await asyncio.to_thread(_csv_load_latest_all, DATA_DIR)


async def init_db() -> None:
    """Create all tables (idempotent). Prefer Alembic for production migrations."""
    if not USE_POSTGRES:
        return
    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("[PG] Tables ensured")
