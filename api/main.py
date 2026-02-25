"""FastAPI app — AI ALPHA PULSE REST API."""
from fastapi import FastAPI, HTTPException
from common.models import ScoringResult, Asset
from common.logger import get_logger, new_request_id
from scoring.aggregator import score_asset
from ingest.yahoo_finance import YahooFinanceIngestor
from ingest.binance import BinanceIngestor

app = FastAPI(title="AI ALPHA PULSE", version="0.1.0")
logger = get_logger("api")

@app.get("/")
def root():
    return {"name": "AI ALPHA PULSE", "version": "0.1.0", "status": "ok"}

@app.get("/score/{ticker}", response_model=ScoringResult)
def get_score(ticker: str, asset_type: str = "stock"):
    new_request_id()
    ticker = ticker.upper()
    logger.info(f"Scoring {ticker} ({asset_type})")
    try:
        if asset_type == "crypto":
            ingestor = BinanceIngestor()
            asset = Asset(ticker=ticker, name=ticker, asset_type="crypto", exchange="Binance")
        else:
            ingestor = YahooFinanceIngestor()
            asset = Asset(ticker=ticker, name=ticker, asset_type="stock", exchange="NYSE")
        df = ingestor.fetch(ticker)
        if df.empty:
            raise HTTPException(status_code=404, detail=f"No data for {ticker}")
        return score_asset(asset, df)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error scoring {ticker}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
def health():
    return {"status": "healthy"}
