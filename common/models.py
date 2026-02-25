"""Core Pydantic models for AI ALPHA PULSE."""
from datetime import datetime
from pydantic import BaseModel

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

    @property
    def signal_emoji(self) -> str:
        return {"STRONG BUY": "🟢🟢", "BUY": "🟢", "NEUTRAL": "🟡",
                "SELL": "🔴", "STRONG SELL": "🔴🔴"}.get(self.signal, "⚪")
