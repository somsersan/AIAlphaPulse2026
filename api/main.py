"""AI ALPHA PULSE — FastAPI REST API with scheduler."""
import asyncio
import json
from pathlib import Path
from typing import List
from fastapi import FastAPI, HTTPException, BackgroundTasks, WebSocket, WebSocketDisconnect, APIRouter
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from contextlib import asynccontextmanager
from datetime import datetime, timezone
import sys
sys.path.insert(0, "/workspace/AIAlphaPulse2026")

from common.models import ScoringResult, Asset
from common.logger import get_logger, new_request_id
from scoring.aggregator import score_asset
from ingest.yahoo_finance import YahooFinanceIngestor
from ingest.binance import BinanceIngestor
from ingest.moex import MOEXIngestor
from storage.database import save_scores, load_history, load_latest_all

logger = get_logger("api")

FRONTEND_DIR = Path(__file__).parent.parent / "frontend"


class ConnectionManager:
    """Manages active WebSocket connections and broadcasts messages."""

    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, payload: dict):
        message = json.dumps(payload)
        dead = []
        for ws in self.active_connections:
            try:
                await ws.send_text(message)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(ws)


manager = ConnectionManager()


TRACKED_ASSETS = [
    # US Stocks — Yahoo Finance
    (Asset(ticker="AAPL",    name="Apple Inc.",        asset_type="stock",  exchange="NASDAQ"), "yahoo"),
    (Asset(ticker="MSFT",    name="Microsoft Corp.",   asset_type="stock",  exchange="NASDAQ"), "yahoo"),
    (Asset(ticker="GOOGL",   name="Alphabet Inc.",     asset_type="stock",  exchange="NASDAQ"), "yahoo"),
    (Asset(ticker="AMZN",    name="Amazon.com Inc.",   asset_type="stock",  exchange="NASDAQ"), "yahoo"),
    (Asset(ticker="TSLA",    name="Tesla Inc.",        asset_type="stock",  exchange="NASDAQ"), "yahoo"),
    (Asset(ticker="NVDA",    name="NVIDIA Corp.",      asset_type="stock",  exchange="NASDAQ"), "yahoo"),
    (Asset(ticker="META",    name="Meta Platforms",    asset_type="stock",  exchange="NASDAQ"), "yahoo"),
    (Asset(ticker="NFLX",    name="Netflix Inc.",      asset_type="stock",  exchange="NASDAQ"), "yahoo"),
    (Asset(ticker="AMD",     name="AMD Inc.",          asset_type="stock",  exchange="NASDAQ"), "yahoo"),
    (Asset(ticker="INTC",    name="Intel Corp.",       asset_type="stock",  exchange="NASDAQ"), "yahoo"),
    # Russian Stocks — MOEX
    (Asset(ticker="SBER",    name="Сбербанк",          asset_type="stock",  exchange="MOEX"),   "moex"),
    (Asset(ticker="GAZP",    name="Газпром",           asset_type="stock",  exchange="MOEX"),   "moex"),
    (Asset(ticker="LKOH",    name="Лукойл",            asset_type="stock",  exchange="MOEX"),   "moex"),
    (Asset(ticker="YNDX",    name="Яндекс",            asset_type="stock",  exchange="MOEX"),   "moex"),
    (Asset(ticker="TCSG",    name="Т-Банк",            asset_type="stock",  exchange="MOEX"),   "moex"),
    (Asset(ticker="MGNT",    name="Магнит",            asset_type="stock",  exchange="MOEX"),   "moex"),
    (Asset(ticker="FIVE",    name="X5 Retail Group",   asset_type="stock",  exchange="MOEX"),   "moex"),
    (Asset(ticker="VKCO",    name="VK Company",        asset_type="stock",  exchange="MOEX"),   "moex"),
    # Crypto — Binance
    (Asset(ticker="BTCUSDT", name="Bitcoin",           asset_type="crypto", exchange="Binance"),"binance"),
    (Asset(ticker="ETHUSDT", name="Ethereum",          asset_type="crypto", exchange="Binance"),"binance"),
    (Asset(ticker="SOLUSDT", name="Solana",            asset_type="crypto", exchange="Binance"),"binance"),
    (Asset(ticker="BNBUSDT", name="BNB",               asset_type="crypto", exchange="Binance"),"binance"),
    (Asset(ticker="XRPUSDT", name="XRP",               asset_type="crypto", exchange="Binance"),"binance"),
    (Asset(ticker="DOGEUSDT",name="Dogecoin",          asset_type="crypto", exchange="Binance"),"binance"),
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
        payload = {
            "type": "scores_update",
            "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "scores": [
                {
                    "ticker": r.asset.ticker,
                    "ai_score": r.ai_score,
                    "signal": r.signal,
                    "trend_score": r.trend_score,
                    "volatility_score": r.volatility_score,
                    "explanation": r.explanation,
                }
                for r in results
            ],
        }
        await manager.broadcast(payload)
    logger.info(f"🏁 Scoring cycle done: {len(results)} assets scored")
    return results

@asynccontextmanager
async def lifespan(app: FastAPI):
    asyncio.create_task(run_scoring_cycle())
    async def scheduler():
        while True:
            await asyncio.sleep(900)
            await run_scoring_cycle()
    asyncio.create_task(scheduler())
    yield

app = FastAPI(title="AI ALPHA PULSE API", version="0.2.0", lifespan=lifespan)

app.add_middleware(CORSMiddleware,
    allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# ── Frontend ──────────────────────────────────────────────────────────────────

@app.get("/", include_in_schema=False)
def serve_frontend():
    return FileResponse(FRONTEND_DIR / "index.html")

@app.get("/logo.jpg", include_in_schema=False)
def serve_logo():
    return FileResponse(FRONTEND_DIR / "logo.jpg")

# ── API routes (on a shared router, mounted at both "/" and "/api") ───────────
# This makes the app work:
#   • locally via browser  → /api/scores  (what index.html calls)
#   • via nginx in Docker  → /scores      (nginx strips /api/ prefix)

router = APIRouter()

@router.get("/health")
def health():
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}

@router.get("/assets")
def get_assets():
    return [{"ticker": a.ticker, "name": a.name,
             "asset_type": a.asset_type, "exchange": a.exchange}
            for a, _ in TRACKED_ASSETS]

@router.get("/scores")
def get_all_scores():
    """Get latest score for all tracked assets."""
    df = load_latest_all()
    if df.empty:
        return {"scores": [], "note": "No scores yet, scoring in progress..."}
    return {"scores": df.to_dict(orient="records"),
            "count": len(df), "timestamp": datetime.utcnow().isoformat()}

@router.get("/score/{ticker}")
def get_score(ticker: str, asset_type: str = "stock"):
    new_request_id()
    ticker = ticker.upper()
    try:
        if asset_type == "crypto":
            ingestor = INGESTORS["binance"]
            asset = Asset(ticker=ticker, name=ticker, asset_type="crypto", exchange="Binance")
        elif ticker in ["SBER","GAZP","LKOH","YNDX","TCSG","MGNT","FIVE","VKCO"]:
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

@router.get("/history/{ticker}")
def get_history(ticker: str, days: int = 30):
    df = load_history(ticker.upper(), days)
    if df.empty:
        return {"ticker": ticker, "history": [], "days": days}
    return {"ticker": ticker, "history": df.to_dict(orient="records"), "days": days}

@router.post("/score/refresh")
async def trigger_refresh(background_tasks: BackgroundTasks):
    """Manually trigger a full scoring cycle."""
    background_tasks.add_task(run_scoring_cycle)
    return {"status": "scoring cycle triggered", "assets": len(TRACKED_ASSETS)}

# Mount routes at root (for nginx) and at /api (for direct browser access)
app.include_router(router)
app.include_router(router, prefix="/api")

# ── WebSocket ─────────────────────────────────────────────────────────────────

@app.websocket("/ws/live")
async def websocket_live(websocket: WebSocket):
    """WebSocket endpoint — pushes score updates in real time."""
    await manager.connect(websocket)
    try:
        df = load_latest_all()
        scores = df.to_dict(orient="records") if not df.empty else []
        await websocket.send_text(json.dumps({
            "type": "scores_update",
            "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "scores": scores,
        }))
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception:
        manager.disconnect(websocket)
