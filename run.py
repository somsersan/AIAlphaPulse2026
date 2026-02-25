"""
AI ALPHA PULSE — Entry point
Run: python run.py
"""
import sys
sys.path.insert(0, "/workspace/AIAlphaPulse2026")

from common.models import Asset
from common.logger import get_logger, new_request_id
from scoring.aggregator import score_asset
from ingest.yahoo_finance import YahooFinanceIngestor
from ingest.binance import BinanceIngestor
from ingest.moex import MOEXIngestor

logger = get_logger("run")

ASSETS_TO_SCORE = [
    (Asset(ticker="AAPL",    name="Apple Inc.",      asset_type="stock",  exchange="NASDAQ"), "yahoo"),
    (Asset(ticker="MSFT",    name="Microsoft Corp.", asset_type="stock",  exchange="NASDAQ"), "yahoo"),
    (Asset(ticker="SBER",    name="Сбербанк",        asset_type="stock",  exchange="MOEX"),   "moex"),
    (Asset(ticker="BTCUSDT", name="Bitcoin",         asset_type="crypto", exchange="Binance"),"binance"),
    (Asset(ticker="ETHUSDT", name="Ethereum",        asset_type="crypto", exchange="Binance"),"binance"),
]

def main():
    new_request_id()
    print("\n" + "="*70)
    print("  🚀  AI ALPHA PULSE v0.1  —  Multi-Factor Asset Scoring")
    print("="*70)
    print(f"{'Ticker':<12} {'Name':<18} {'Trend':>7} {'Volatil':>8} {'AI SCORE':>10}  Signal")
    print("-"*70)

    ingestors = {
        "yahoo":   YahooFinanceIngestor(),
        "binance": BinanceIngestor(),
        "moex":    MOEXIngestor(),
    }

    for asset, source in ASSETS_TO_SCORE:
        try:
            df = ingestors[source].fetch(asset.ticker)
            result = score_asset(asset, df)
            emoji = {"STRONG BUY":"🟢🟢","BUY":"🟢","NEUTRAL":"🟡","SELL":"🔴","STRONG SELL":"🔴🔴"}.get(result.signal,"⚪")
            print(f"{asset.ticker:<12} {asset.name:<18} {result.trend_score:>7.1f} {result.volatility_score:>8.1f} {result.ai_score:>10.1f}  {emoji} {result.signal}")
        except Exception as e:
            logger.error(f"Failed to score {asset.ticker}: {e}")
            print(f"{asset.ticker:<12} {'ERROR':<18} {'—':>7} {'—':>8} {'—':>10}  ❌ {e}")

    print("="*70)
    print("  ℹ️  AI SCORE range: -100 (STRONG SELL) → +100 (STRONG BUY)")
    print("="*70 + "\n")

if __name__ == "__main__":
    main()
