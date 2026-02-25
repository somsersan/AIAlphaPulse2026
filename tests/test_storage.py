"""Tests for storage module."""
import sys, os
sys.path.insert(0, "/workspace/AIAlphaPulse2026")
import pytest
from datetime import datetime
from common.models import Asset, ScoringResult
from storage import database

def make_result(ticker="AAPL", score=45.0):
    return ScoringResult(
        asset=Asset(ticker=ticker, name=ticker, asset_type="stock", exchange="TEST"),
        timestamp=datetime.utcnow(),
        trend_score=30.0, volatility_score=20.0, ai_score=score,
        signal="BUY", explanation="test"
    )

class TestStorage:
    def test_save_and_load(self, tmp_path, monkeypatch):
        monkeypatch.setattr(database, "DATA_DIR", tmp_path)
        results = [make_result("AAPL", 45.0), make_result("BTC", -20.0)]
        database.save_scores(results)
        df = database.load_latest_all()
        assert len(df) == 2
        assert "AAPL" in df["ticker"].values

    def test_load_history(self, tmp_path, monkeypatch):
        monkeypatch.setattr(database, "DATA_DIR", tmp_path)
        database.save_scores([make_result("AAPL", 50.0)])
        df = database.load_history("AAPL", days=30)
        assert len(df) == 1
        assert df.iloc[0]["ticker"] == "AAPL"
