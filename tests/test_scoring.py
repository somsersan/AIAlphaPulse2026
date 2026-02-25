"""Tests for scoring modules."""
import sys
sys.path.insert(0, "/workspace/AIAlphaPulse2026")
import pandas as pd
import numpy as np
import pytest
from scoring.trend import TrendScorer
from scoring.volatility import VolatilityScorer
from scoring.sentiment import SentimentScorer
from scoring.aggregator import score_asset, signal_from_score
from common.models import Asset

def make_df(n=90, trend="flat"):
    dates = pd.date_range(end=pd.Timestamp.now(), periods=n, freq="D")
    np.random.seed(42)
    if trend == "up":
        price = np.linspace(100, 150, n) + np.random.randn(n) * 0.5
    elif trend == "down":
        price = np.linspace(150, 100, n) + np.random.randn(n) * 0.5
    else:
        price = 100 + np.random.randn(n) * 2
    price = np.abs(price)
    return pd.DataFrame({
        "open": price * 0.99, "high": price * 1.01,
        "low":  price * 0.98, "close": price,
        "volume": np.random.randint(1_000_000, 10_000_000, n).astype(float)
    }, index=dates)

class TestTrendScorer:
    def setup_method(self):
        self.scorer = TrendScorer()

    def test_returns_float(self):
        df = make_df()
        assert isinstance(self.scorer.score(df), float)

    def test_score_in_range(self):
        for trend in ["up","down","flat"]:
            score = self.scorer.score(make_df(trend=trend))
            assert -100 <= score <= 100, f"Score out of range for {trend}: {score}"

    def test_uptrend_positive(self):
        score = self.scorer.score(make_df(trend="up"))
        assert score > 0, f"Expected positive for uptrend, got {score}"

    def test_downtrend_negative(self):
        score = self.scorer.score(make_df(trend="down"))
        assert score < 0, f"Expected negative for downtrend, got {score}"

    def test_short_df_returns_zero(self):
        df = make_df(n=10)
        assert self.scorer.score(df) == 0.0

class TestVolatilityScorer:
    def setup_method(self):
        self.scorer = VolatilityScorer()

    def test_returns_float(self):
        assert isinstance(self.scorer.score(make_df()), float)

    def test_score_in_range(self):
        score = self.scorer.score(make_df())
        assert -100 <= score <= 100

    def test_short_df_returns_zero(self):
        assert self.scorer.score(make_df(n=5)) == 0.0

class TestSentimentScorer:
    def setup_method(self):
        self.scorer = SentimentScorer()

    def test_positive_news(self):
        news = [{"sentiment": 0.8}, {"sentiment": 0.9}, {"sentiment": 0.7}]
        score = self.scorer.score(make_df(), news=news)
        assert score > 0

    def test_negative_news(self):
        news = [{"sentiment": -0.8}, {"sentiment": -0.6}]
        score = self.scorer.score(make_df(), news=news)
        assert score < 0

    def test_no_news_uses_price(self):
        score = self.scorer.score(make_df())
        assert isinstance(score, float)
        assert -100 <= score <= 100

class TestAggregator:
    def test_signal_from_score(self):
        assert signal_from_score(80) == "STRONG BUY"
        assert signal_from_score(40) == "BUY"
        assert signal_from_score(0) == "NEUTRAL"
        assert signal_from_score(-40) == "SELL"
        assert signal_from_score(-80) == "STRONG SELL"

    def test_score_asset_returns_result(self):
        asset = Asset(ticker="TEST", name="Test Asset", asset_type="stock", exchange="TEST")
        result = score_asset(asset, make_df())
        assert result.ai_score is not None
        assert -100 <= result.ai_score <= 100
        assert result.signal in ["STRONG BUY","BUY","NEUTRAL","SELL","STRONG SELL"]

    def test_score_asset_all_fields(self):
        asset = Asset(ticker="TEST", name="Test", asset_type="stock", exchange="TEST")
        result = score_asset(asset, make_df())
        assert result.trend_score is not None
        assert result.volatility_score is not None
        assert result.explanation is not None
