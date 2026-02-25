"""
AI ALPHA PULSE v0.3 — Entry point
Показывает полный скоринг по всем 7 факторам.
Run: python run.py
"""
import sys, warnings
warnings.filterwarnings("ignore")
sys.path.insert(0, "/workspace/AIAlphaPulse2026")

from common.models import Asset
from common.logger import get_logger, new_request_id
from scoring.aggregator import score_asset, WEIGHTS
from ingest.yahoo_finance import YahooFinanceIngestor
from ingest.binance import BinanceIngestor
from ingest.moex import MOEXIngestor

logger = get_logger("run")

ASSETS_TO_SCORE = [
    (Asset(ticker="AAPL",    name="Apple Inc.",      asset_type="stock",  exchange="NASDAQ"), "yahoo",   "AAPL"),
    (Asset(ticker="MSFT",    name="Microsoft Corp.", asset_type="stock",  exchange="NASDAQ"), "yahoo",   "MSFT"),
    (Asset(ticker="GOOGL",   name="Alphabet Inc.",   asset_type="stock",  exchange="NASDAQ"), "yahoo",   "GOOGL"),
    (Asset(ticker="SBER",    name="Сбербанк",        asset_type="stock",  exchange="MOEX"),   "moex",    None),
    (Asset(ticker="BTCUSDT", name="Bitcoin",         asset_type="crypto", exchange="Binance"),"binance", None),
    (Asset(ticker="ETHUSDT", name="Ethereum",        asset_type="crypto", exchange="Binance"),"binance", None),
]

FACTOR_LABELS = {
    "trend":             "Trend",
    "sentiment":         "Sentiment",
    "fundamental":       "Fundament",
    "relative_strength": "Rel.Str.",
    "volatility":        "Volat.",
    "insider_funds":     "Insider",
    "macro":             "Macro",
}

def main():
    new_request_id()
    ingestors = {
        "yahoo":   YahooFinanceIngestor(),
        "binance": BinanceIngestor(),
        "moex":    MOEXIngestor(),
    }

    print("\n" + "="*90)
    print("  🚀  AI ALPHA PULSE v0.3  —  7-Factor Multi-Agent Scoring")
    print("="*90)
    hdr = f"{'Ticker':<10} {'Trend':>7} {'Sntmt':>6} {'Fund':>6} {'RS':>6} {'Volt':>6} {'Ins':>6} {'Macro':>6} {'AI SCORE':>10}  Signal"
    print(hdr)
    print("-"*90)

    for asset, source, yf_ticker in ASSETS_TO_SCORE:
        try:
            df = ingestors[source].fetch(asset.ticker)
            result = score_asset(asset, df)
            fs = result.factor_scores

            emoji = {"STRONG BUY":"🟢🟢","BUY":"🟢","NEUTRAL":"🟡",
                     "SELL":"🔴","STRONG SELL":"🔴🔴"}.get(result.signal,"⚪")

            print(
                f"{asset.ticker:<10}"
                f" {fs.get('trend',0):>7.1f}"
                f" {fs.get('sentiment',0):>6.1f}"
                f" {fs.get('fundamental',0):>6.1f}"
                f" {fs.get('relative_strength',0):>6.1f}"
                f" {fs.get('volatility',0):>6.1f}"
                f" {fs.get('insider_funds',0):>6.1f}"
                f" {fs.get('macro',0):>6.1f}"
                f" {result.ai_score:>10.1f}"
                f"  {emoji} {result.signal}"
            )
        except Exception as e:
            print(f"{asset.ticker:<10} {'ERROR':>70}  ❌ {e}")

    print("="*90)
    print(f"\n  Веса: " + " | ".join(f"{k}: {v:.0%}" for k,v in WEIGHTS.items()))
    print("  AI SCORE: -100 (STRONG SELL) → +100 (STRONG BUY)")
    print("="*90 + "\n")

if __name__ == "__main__":
    main()
