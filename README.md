# 🚀 AI ALPHA PULSE

> Мультифакторный AI-скоринг акций и крипто-активов в реальном времени.

## Что это

Каждый актив получает **AI SCORE** от -100 до +100 на основе:
- 📈 **Trend** (MA20/50 crossover, RSI, momentum)
- 📊 **Volatility** (ATR, Bollinger Bands)
- *(следующие блоки: Fundamental, Sentiment, Macro, Insider/Funds, Relative Strength)*

## Быстрый старт

```bash
pip install -r requirements.txt
python run.py
```

## API

```bash
uvicorn api.main:app --reload
# GET /score/AAPL?asset_type=stock
# GET /score/BTCUSDT?asset_type=crypto
```

## Структура

```
ingest/    — парсеры данных (Yahoo Finance, Binance, MOEX)
scoring/   — движок скоринга (Z-score нормализация)
api/       — FastAPI REST API
common/    — модели, логгер
run.py     — точка входа
```

## Источники данных (бесплатные)
- Yahoo Finance (акции глобальные)
- Binance Public API (крипто)
- MOEX ISS API (российские акции)
