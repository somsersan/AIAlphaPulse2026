# AI ALPHA PULSE — Architecture

## System Overview
```
┌──────────────────────────────────────────────────────────────┐
│                      AI ALPHA PULSE                          │
├──────────┬───────────┬──────────┬──────────┬────────────────┤
│  INGEST  │  PROCESS  │  SCORE   │   API    │   FRONTEND     │
│ Yahoo    │ Clean     │ Trend    │ FastAPI  │ React Dashboard│
│ Binance  │ Normalize │ Volatil  │ REST     │ Score Table    │
│ MOEX     │ Enrich    │ Sentiment│ WebSocket│ Sparkline Chart│
│ AlphaV   │ Dedup     │ Fundament│ Auth JWT │ Signal Badges  │
└──────────┴───────────┴──────────┴──────────┴────────────────┘
                            │
                     PostgreSQL DB
               (assets, ohlcv, scores)
                            │
                    APScheduler (15min)
```

## Database Schema

```sql
CREATE TABLE assets (
    id SERIAL PRIMARY KEY,
    ticker VARCHAR(20) UNIQUE NOT NULL,
    name VARCHAR(100),
    asset_type VARCHAR(20),
    exchange VARCHAR(50),
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE ohlcv_data (
    id BIGSERIAL PRIMARY KEY,
    asset_id INTEGER REFERENCES assets(id),
    timestamp TIMESTAMP NOT NULL,
    open DECIMAL(20,8), high DECIMAL(20,8),
    low DECIMAL(20,8), close DECIMAL(20,8), volume DECIMAL(30,8),
    UNIQUE(asset_id, timestamp)
);

CREATE TABLE scoring_results (
    id BIGSERIAL PRIMARY KEY,
    asset_id INTEGER REFERENCES assets(id),
    timestamp TIMESTAMP NOT NULL,
    trend_score DECIMAL(6,2), volatility_score DECIMAL(6,2),
    sentiment_score DECIMAL(6,2), fundamental_score DECIMAL(6,2),
    ai_score DECIMAL(6,2), signal VARCHAR(20), explanation TEXT,
    UNIQUE(asset_id, timestamp)
);
```

## API Endpoints
| Method | Path | Description |
|--------|------|-------------|
| GET | /scores | All assets latest scores |
| GET | /score/{ticker} | Single asset score |
| GET | /history/{ticker} | Score history |
| GET | /assets | List assets |
| WS  | /ws/live | Live score stream |
