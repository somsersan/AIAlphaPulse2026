#!/usr/bin/env python3
"""
Standalone scheduler — score all assets and save results.
Run: python scheduler.py
Or add to cron: */15 * * * * cd /workspace/AIAlphaPulse2026 && ./venv/bin/python scheduler.py
"""
import sys
sys.path.insert(0, "/workspace/AIAlphaPulse2026")

from common.models import Asset
from common.logger import get_logger, new_request_id
from scoring.aggregator import score_asset
from ingest.yahoo_finance import YahooFinanceIngestor
from ingest.binance import BinanceIngestor
from ingest.moex import MOEXIngestor
from storage.database import save_scores
from datetime import datetime

logger = get_logger("scheduler")

ASSETS = [
    (Asset(ticker="AAPL",    name="Apple Inc.",      asset_type="stock",  exchange="NASDAQ"), "yahoo"),
    (Asset(ticker="MSFT",    name="Microsoft Corp.", asset_type="stock",  exchange="NASDAQ"), "yahoo"),
    (Asset(ticker="GOOGL",   name="Alphabet Inc.",   asset_type="stock",  exchange="NASDAQ"), "yahoo"),
    (Asset(ticker="SBER",    name="Сбербанк",        asset_type="stock",  exchange="MOEX"),   "moex"),
    (Asset(ticker="GAZP",    name="Газпром",         asset_type="stock",  exchange="MOEX"),   "moex"),
    (Asset(ticker="BTCUSDT", name="Bitcoin",         asset_type="crypto", exchange="Binance"),"binance"),
    (Asset(ticker="ETHUSDT", name="Ethereum",        asset_type="crypto", exchange="Binance"),"binance"),
    (Asset(ticker="SOLUSDT", name="Solana",          asset_type="crypto", exchange="Binance"),"binance"),
]

def main():
    new_request_id()
    logger.info(f"🚀 Scoring cycle started at {datetime.utcnow().isoformat()}")
    ingestors = {"yahoo": YahooFinanceIngestor(), "binance": BinanceIngestor(), "moex": MOEXIngestor()}
    results = []
    for asset, source in ASSETS:
        try:
            df = ingestors[source].fetch(asset.ticker)
            result = score_asset(asset, df)
            results.append(result)
            emoji = {"STRONG BUY":"🟢🟢","BUY":"🟢","NEUTRAL":"🟡","SELL":"🔴","STRONG SELL":"🔴🔴"}.get(result.signal,"⚪")
            print(f"{asset.ticker:<12} {result.ai_score:>7.1f}  {emoji} {result.signal}")
        except Exception as e:
            logger.error(f"❌ {asset.ticker}: {e}")
    save_scores(results)
    logger.info(f"✅ Done: {len(results)}/{len(ASSETS)} assets scored")

if __name__ == "__main__":
    main()
