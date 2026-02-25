"""Tests for ingest modules."""
import sys
sys.path.insert(0, "/workspace/AIAlphaPulse2026")
import pandas as pd
import pytest
from ingest.yahoo_finance import YahooFinanceIngestor
from ingest.binance import BinanceIngestor
from ingest.moex import MOEXIngestor

REQUIRED_COLS = {"open","high","low","close","volume"}

class TestYahooFinance:
    def setup_method(self):
        self.ing = YahooFinanceIngestor()

    def test_mock_returns_dataframe(self):
        df = self.ing._mock_data("AAPL")
        assert isinstance(df, pd.DataFrame)
        assert not df.empty

    def test_mock_has_required_columns(self):
        df = self.ing._mock_data("AAPL")
        assert REQUIRED_COLS.issubset(set(df.columns))

    def test_mock_has_90_rows(self):
        df = self.ing._mock_data("AAPL")
        assert len(df) == 90

    def test_mock_no_negative_prices(self):
        df = self.ing._mock_data("AAPL")
        assert (df["close"] > 0).all()

    def test_fetch_returns_dataframe(self):
        df = self.ing.fetch("AAPL")
        assert isinstance(df, pd.DataFrame)
        assert not df.empty
        assert REQUIRED_COLS.issubset(set(df.columns))

    def test_different_tickers_different_data(self):
        df1 = self.ing._mock_data("AAPL")
        df2 = self.ing._mock_data("MSFT")
        assert not df1["close"].equals(df2["close"])

class TestBinance:
    def setup_method(self):
        self.ing = BinanceIngestor()

    def test_mock_returns_dataframe(self):
        df = self.ing._mock_data("BTCUSDT")
        assert isinstance(df, pd.DataFrame)
        assert not df.empty

    def test_mock_btc_higher_than_eth(self):
        btc = self.ing._mock_data("BTCUSDT")["close"].mean()
        eth = self.ing._mock_data("ETHUSDT")["close"].mean()
        assert btc > eth

    def test_fetch_live_or_mock(self):
        df = self.ing.fetch("BTCUSDT")
        assert isinstance(df, pd.DataFrame)
        assert len(df) > 0

class TestMOEX:
    def setup_method(self):
        self.ing = MOEXIngestor()

    def test_mock_returns_dataframe(self):
        df = self.ing._mock_data("SBER")
        assert isinstance(df, pd.DataFrame)

    def test_fetch_returns_data(self):
        df = self.ing.fetch("SBER")
        assert isinstance(df, pd.DataFrame)
        assert len(df) > 0
