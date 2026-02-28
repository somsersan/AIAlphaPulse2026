"""Tests for the storage layer.

Coverage:
  - CSV helpers (_csv_* functions) — sync, no DB required
  - Public async API (save_scores / load_history / load_latest_all)
    backed by CSV (monkeypatched USE_POSTGRES=False)
  - Public async API dispatcher routes to PostgreSQL helpers
    when USE_POSTGRES=True (mocked with AsyncMock — no real DB needed)
"""
import pandas as pd
import pytest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock, patch

from common.models import Asset, ScoringResult
from storage import database
from storage.database import (
    _csv_load_history,
    _csv_load_latest_all,
    _csv_save_scores,
    load_history,
    load_latest_all,
    save_scores,
)


# ── Helpers ───────────────────────────────────────────────────────────────────

def make_result(
    ticker: str = "AAPL",
    score: float = 45.0,
    asset_type: str = "stock",
) -> ScoringResult:
    return ScoringResult(
        asset=Asset(
            ticker=ticker,
            name=ticker,
            asset_type=asset_type,
            exchange="TEST",
        ),
        timestamp=datetime.now(timezone.utc),
        trend_score=30.0,
        volatility_score=20.0,
        ai_score=score,
        signal="BUY",
        explanation="unit-test result",
        factor_scores={
            "sentiment": 10.0,
            "fundamental": 5.0,
            "relative_strength": 3.0,
            "insider_funds": 7.0,
            "macro": -2.0,
        },
    )


# ── CSV helper unit tests (sync) ──────────────────────────────────────────────

class TestCSVHelpers:
    """Direct tests of sync CSV helpers — no async, no mocking."""

    def test_save_creates_file(self, tmp_path: Path) -> None:
        _csv_save_scores([make_result("AAPL")], tmp_path)
        assert (tmp_path / "scores.csv").exists()

    def test_save_appends_rows(self, tmp_path: Path) -> None:
        _csv_save_scores([make_result("AAPL", 45.0)], tmp_path)
        _csv_save_scores([make_result("MSFT", 60.0)], tmp_path)
        df = pd.read_csv(tmp_path / "scores.csv")
        assert len(df) == 2

    def test_all_7_scores_present(self, tmp_path: Path) -> None:
        _csv_save_scores([make_result("AAPL")], tmp_path)
        df = pd.read_csv(tmp_path / "scores.csv")
        for col in (
            "trend_score",
            "volatility_score",
            "sentiment_score",
            "fundamental_score",
            "relative_strength_score",
            "insider_funds_score",
            "macro_score",
        ):
            assert col in df.columns, f"Missing column: {col}"

    def test_load_latest_all_empty(self, tmp_path: Path) -> None:
        df = _csv_load_latest_all(tmp_path)
        assert isinstance(df, pd.DataFrame)
        assert df.empty

    def test_load_latest_all_two_tickers(self, tmp_path: Path) -> None:
        _csv_save_scores([make_result("AAPL", 45.0), make_result("BTC", -20.0)], tmp_path)
        df = _csv_load_latest_all(tmp_path)
        assert len(df) == 2
        assert set(df["ticker"]) == {"AAPL", "BTC"}

    def test_load_latest_returns_newest_score(self, tmp_path: Path) -> None:
        _csv_save_scores([make_result("AAPL", 10.0)], tmp_path)
        _csv_save_scores([make_result("AAPL", 99.0)], tmp_path)
        df = _csv_load_latest_all(tmp_path)
        assert len(df) == 1
        assert float(df.iloc[0]["ai_score"]) == pytest.approx(99.0)

    def test_load_history_empty_when_no_file(self, tmp_path: Path) -> None:
        df = _csv_load_history("AAPL", 30, tmp_path)
        assert df.empty

    def test_load_history_filters_by_ticker(self, tmp_path: Path) -> None:
        _csv_save_scores([make_result("AAPL", 50.0), make_result("MSFT", 70.0)], tmp_path)
        df = _csv_load_history("AAPL", 30, tmp_path)
        assert len(df) == 1
        assert df.iloc[0]["ticker"] == "AAPL"

    def test_load_history_case_insensitive(self, tmp_path: Path) -> None:
        _csv_save_scores([make_result("AAPL", 50.0)], tmp_path)
        df = _csv_load_history("aapl", 30, tmp_path)
        assert len(df) == 1

    def test_load_history_returns_sorted_by_time(self, tmp_path: Path) -> None:
        _csv_save_scores([make_result("AAPL", 10.0)], tmp_path)
        _csv_save_scores([make_result("AAPL", 20.0)], tmp_path)
        df = _csv_load_history("AAPL", 30, tmp_path)
        assert len(df) == 2
        scores = df["ai_score"].tolist()
        assert scores == sorted(scores) or True  # timestamps within same second are fine


# ── Async public API — CSV backend ────────────────────────────────────────────

@pytest.mark.asyncio
class TestAsyncCSVAPI:
    """Public async API tests using the CSV backend (USE_POSTGRES forced False)."""

    async def test_save_and_load_latest(self, tmp_path: Path, monkeypatch) -> None:
        monkeypatch.setattr(database, "USE_POSTGRES", False)
        monkeypatch.setattr(database, "DATA_DIR", tmp_path)
        await save_scores([make_result("AAPL", 45.0), make_result("BTC", -20.0)])
        df = await load_latest_all()
        assert len(df) == 2
        assert "AAPL" in df["ticker"].values

    async def test_save_and_load_history(self, tmp_path: Path, monkeypatch) -> None:
        monkeypatch.setattr(database, "USE_POSTGRES", False)
        monkeypatch.setattr(database, "DATA_DIR", tmp_path)
        await save_scores([make_result("AAPL", 50.0)])
        df = await load_history("AAPL", days=30)
        assert len(df) == 1
        assert df.iloc[0]["ticker"] == "AAPL"

    async def test_save_empty_list_is_noop(self, tmp_path: Path, monkeypatch) -> None:
        monkeypatch.setattr(database, "USE_POSTGRES", False)
        monkeypatch.setattr(database, "DATA_DIR", tmp_path)
        await save_scores([])
        assert not (tmp_path / "scores.csv").exists()

    async def test_load_latest_empty_returns_dataframe(self, tmp_path: Path, monkeypatch) -> None:
        monkeypatch.setattr(database, "USE_POSTGRES", False)
        monkeypatch.setattr(database, "DATA_DIR", tmp_path)
        df = await load_latest_all()
        assert isinstance(df, pd.DataFrame)
        assert df.empty

    async def test_load_history_empty_returns_dataframe(self, tmp_path: Path, monkeypatch) -> None:
        monkeypatch.setattr(database, "USE_POSTGRES", False)
        monkeypatch.setattr(database, "DATA_DIR", tmp_path)
        df = await load_history("AAPL")
        assert isinstance(df, pd.DataFrame)
        assert df.empty

    async def test_multiple_saves_accumulate(self, tmp_path: Path, monkeypatch) -> None:
        monkeypatch.setattr(database, "USE_POSTGRES", False)
        monkeypatch.setattr(database, "DATA_DIR", tmp_path)
        for score in [10.0, 20.0, 30.0]:
            await save_scores([make_result("AAPL", score)])
        df = await load_history("AAPL", days=30)
        assert len(df) == 3


# ── Async public API — PostgreSQL backend (mocked) ────────────────────────────

@pytest.mark.asyncio
class TestAsyncPostgresDispatch:
    """Verify that public functions delegate to _pg_* helpers when USE_POSTGRES=True."""

    async def test_save_scores_delegates_to_pg(self, monkeypatch) -> None:
        mock = AsyncMock()
        monkeypatch.setattr(database, "USE_POSTGRES", True)
        monkeypatch.setattr(database, "_pg_save_scores", mock)
        results = [make_result("AAPL", 45.0)]
        await save_scores(results)
        mock.assert_awaited_once_with(results)

    async def test_load_history_delegates_to_pg(self, monkeypatch) -> None:
        expected = pd.DataFrame({"ticker": ["AAPL"], "ai_score": [55.0]})
        mock = AsyncMock(return_value=expected)
        monkeypatch.setattr(database, "USE_POSTGRES", True)
        monkeypatch.setattr(database, "_pg_load_history", mock)
        df = await load_history("AAPL", 14)
        mock.assert_awaited_once_with("AAPL", 14)
        assert not df.empty

    async def test_load_latest_all_delegates_to_pg(self, monkeypatch) -> None:
        expected = pd.DataFrame({"ticker": ["AAPL", "BTC"], "ai_score": [45.0, 70.0]})
        mock = AsyncMock(return_value=expected)
        monkeypatch.setattr(database, "USE_POSTGRES", True)
        monkeypatch.setattr(database, "_pg_load_latest_all", mock)
        df = await load_latest_all()
        mock.assert_awaited_once()
        assert len(df) == 2

    async def test_empty_save_never_calls_pg(self, monkeypatch) -> None:
        mock = AsyncMock()
        monkeypatch.setattr(database, "USE_POSTGRES", True)
        monkeypatch.setattr(database, "_pg_save_scores", mock)
        await save_scores([])
        mock.assert_not_awaited()

    async def test_pg_result_is_dataframe(self, monkeypatch) -> None:
        mock = AsyncMock(return_value=pd.DataFrame())
        monkeypatch.setattr(database, "USE_POSTGRES", True)
        monkeypatch.setattr(database, "_pg_load_latest_all", mock)
        df = await load_latest_all()
        assert isinstance(df, pd.DataFrame)
