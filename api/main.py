"""AI ALPHA PULSE — FastAPI REST API with scheduler."""
import asyncio
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
from datetime import datetime
import sys, os
sys.path.insert(0, "/workspace/AIAlphaPulse2026")

from common.models import ScoringResult, Asset
from common.logger import get_logger, new_request_id
from scoring.aggregator import score_asset
from ingest.yahoo_finance import YahooFinanceIngestor
from ingest.binance import BinanceIngestor
from ingest.moex import MOEXIngestor
from storage.database import save_scores, load_history, load_latest_all

logger = get_logger("api")

TRACKED_ASSETS = [
    (Asset(ticker="AAPL",    name="Apple Inc.",      asset_type="stock",  exchange="NASDAQ"), "yahoo"),
    (Asset(ticker="MSFT",    name="Microsoft Corp.", asset_type="stock",  exchange="NASDAQ"), "yahoo"),
    (Asset(ticker="GOOGL",   name="Alphabet Inc.",   asset_type="stock",  exchange="NASDAQ"), "yahoo"),
    (Asset(ticker="SBER",    name="Сбербанк",        asset_type="stock",  exchange="MOEX"),   "moex"),
    (Asset(ticker="GAZP",    name="Газпром",         asset_type="stock",  exchange="MOEX"),   "moex"),
    (Asset(ticker="BTCUSDT", name="Bitcoin",         asset_type="crypto", exchange="Binance"),"binance"),
    (Asset(ticker="ETHUSDT", name="Ethereum",        asset_type="crypto", exchange="Binance"),"binance"),
    (Asset(ticker="SOLUSDT", name="Solana",          asset_type="crypto", exchange="Binance"),"binance"),
]

INGESTORS = {
    "yahoo":   YahooFinanceIngestor(),
    "binance": BinanceIngestor(),
    "moex":    MOEXIngestor(),
}

async def run_scoring_cycle():
    """Score all tracked assets and save results."""
    logger.info("🔄 Starting scoring cycle...")
    results = []
    for asset, source in TRACKED_ASSETS:
        try:
            df = INGESTORS[source].fetch(asset.ticker)
            result = score_asset(asset, df)
            results.append(result)
            logger.info(f"✅ {asset.ticker}: AI SCORE={result.ai_score} {result.signal}")
        except Exception as e:
            logger.error(f"❌ Failed {asset.ticker}: {e}")
    if results:
        save_scores(results)
    logger.info(f"🏁 Scoring cycle done: {len(results)} assets scored")
    return results

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Run initial scoring on startup
    asyncio.create_task(run_scoring_cycle())
    # Schedule every 15 min
    async def scheduler():
        while True:
            await asyncio.sleep(900)  # 15 min
            await run_scoring_cycle()
    asyncio.create_task(scheduler())
    yield

app = FastAPI(title="AI ALPHA PULSE API", version="0.2.0", lifespan=lifespan)

app.add_middleware(CORSMiddleware,
    allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

@app.get("/")
def root():
    return {"name": "AI ALPHA PULSE", "version": "0.2.0", "status": "running",
            "assets_tracked": len(TRACKED_ASSETS)}

@app.get("/health")
def health():
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}

@app.get("/assets")
def get_assets():
    return [{"ticker": a.ticker, "name": a.name,
             "asset_type": a.asset_type, "exchange": a.exchange}
            for a, _ in TRACKED_ASSETS]

@app.get("/scores")
def get_all_scores():
    """Get latest score for all tracked assets."""
    import pandas as pd
    df = load_latest_all()
    if df.empty:
        return {"scores": [], "note": "No scores yet, scoring in progress..."}
    return {"scores": df.to_dict(orient="records"),
            "count": len(df), "timestamp": datetime.utcnow().isoformat()}

@app.get("/score/{ticker}")
def get_score(ticker: str, asset_type: str = "stock"):
    new_request_id()
    ticker = ticker.upper()
    try:
        if asset_type == "crypto":
            ingestor = INGESTORS["binance"]
            asset = Asset(ticker=ticker, name=ticker, asset_type="crypto", exchange="Binance")
        elif ticker in ["SBER","GAZP","LKOH","YNDX","MGNT"]:
            ingestor = INGESTORS["moex"]
            asset = Asset(ticker=ticker, name=ticker, asset_type="stock", exchange="MOEX")
        else:
            ingestor = INGESTORS["yahoo"]
            asset = Asset(ticker=ticker, name=ticker, asset_type="stock", exchange="NYSE")
        df = ingestor.fetch(ticker)
        if df.empty:
            raise HTTPException(404, f"No data for {ticker}")
        return score_asset(asset, df)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, str(e))

@app.get("/history/{ticker}")
def get_history(ticker: str, days: int = 30):
    df = load_history(ticker.upper(), days)
    if df.empty:
        return {"ticker": ticker, "history": [], "days": days}
    return {"ticker": ticker, "history": df.to_dict(orient="records"), "days": days}

@app.post("/score/refresh")
async def trigger_refresh(background_tasks: BackgroundTasks):
    """Manually trigger a full scoring cycle."""
    background_tasks.add_task(run_scoring_cycle)
    return {"status": "scoring cycle triggered", "assets": len(TRACKED_ASSETS)}
