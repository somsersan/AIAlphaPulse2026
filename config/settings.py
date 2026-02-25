"""Configuration loader."""
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

ALPHA_VANTAGE_API_KEY = os.getenv("ALPHA_VANTAGE_API_KEY", "")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

ASSETS = {
    "stocks": ["AAPL", "MSFT", "GOOGL"],
    "crypto": ["BTCUSDT", "ETHUSDT", "SOLUSDT"],
    "moex": ["SBER", "GAZP", "LKOH"],
}

SCORING_WEIGHTS = {
    "trend": 0.4,
    "volatility": 0.3,
    "sentiment": 0.3,
}
