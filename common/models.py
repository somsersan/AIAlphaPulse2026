"""Core Pydantic models for AI ALPHA PULSE."""
from datetime import datetime
from pydantic import BaseModel
from typing import Optional

class Asset(BaseModel):
    ticker: str
    name: str
    asset_type: str  # "stock" | "crypto"
    exchange: str

class ScoringResult(BaseModel):
    asset: Asset
    timestamp: datetime
    trend_score: float
    volatility_score: float
    ai_score: float
    signal: str
    explanation: str
    factor_scores: dict = {}   # все 7 факторов
    weights: dict = {}         # веса для объяснения

    @property
    def signal_emoji(self) -> str:
        return {"STRONG BUY":"🟢🟢","BUY":"🟢","NEUTRAL":"🟡",
                "SELL":"🔴","STRONG SELL":"🔴🔴"}.get(self.signal,"⚪")
