# AI ALPHA PULSE — Что реализовано

_Версия: v0.4.1 | Последнее обновление: 2026-03-03_

---

## Общая картина

Платформа мультифакторного AI-скоринга финансовых активов.
7 независимых агентов → AI SCORE от -100 до +100 → сигнал BUY/SELL.

**Статус:** Бэкенд полностью готов. Фронтенд — дашборд + детальная карточка актива готовы.

---

## Инфраструктура

| Компонент | Статус | Детали |
|-----------|--------|--------|
| Python 3.11 + FastAPI | ✅ | `api/main.py`, `uvicorn api.main:app` |
| PostgreSQL + asyncpg | ✅ | Async SQLAlchemy, работает через `DATABASE_URL` |
| CSV fallback | ✅ | `DATABASE_URL=none` → `data/scores.csv` |
| Alembic миграции | ✅ | `alembic/versions/001_initial_schema.py` |
| APScheduler | ✅ | Автоскоринг каждые 15 минут (внутри FastAPI lifespan) |
| Docker + docker-compose | ✅ | API сервис + nginx reverse proxy |
| GitHub Actions CI | ✅ | `.github/workflows/ci.yml` — pytest на каждый push/PR |
| nginx конфиг | ✅ | `nginx.conf` — proxy на :8000, статика фронтенда |

---

## Сбор данных (Ingest)

| Источник | Файл | Данные | Mock fallback |
|----------|------|--------|---------------|
| Yahoo Finance | `ingest/yahoo_finance.py` | OHLCV глобальные акции + фундаментал | ✅ |
| Binance Public API | `ingest/binance.py` | Крипто OHLCV + объёмы | ✅ |
| MOEX ISS API | `ingest/moex.py` | Российские акции OHLCV | ✅ |
| Alpha Vantage | `ingest/alpha_vantage.py` | Новости + OHLCV (требует API ключ) | ✅ |

Все 4 ingestor'а наследуются от `BaseIngestor` (`ingest/base.py`).
При недоступности источника — автоматический fallback на mock-данные с логированием.

---

## Scoring Engine — 7 агентов

Все агенты реализованы, используют реальные данные.
Z-score нормализация (`normalize_zscore()` из `scoring/base.py`), выход [-100, +100].

| Агент | Файл | Вес | Индикаторы |
|-------|------|-----|------------|
| Trend | `scoring/trend.py` | **35%** | MA20/50 crossover, RSI(14), 5d momentum |
| Sentiment | `scoring/sentiment.py` | **20%** | CCI, Williams %R, VPT, Alpha Vantage News |
| Fundamental | `scoring/fundamental.py` | **20%** | P/E, P/B, ROE, Revenue Growth, D/E, Margins |
| Relative Strength | `scoring/relative_strength.py` | **10%** | vs S&P500/BTC за 5/10/20/60 дней |
| Volatility | `scoring/volatility.py` | **5%** | ATR(14), Bollinger Band width |
| Insider/Funds | `scoring/insider_funds.py` | **5%** | OBV, Volume Surge, институц. владение |
| Macro | `scoring/macro.py` | **5%** | VIX, DXY, 10Y TNX, S&P500 тренд |

**Итоговая формула:**
```
AI_SCORE = Σ(factor_score × weight)
```
Веса в `scoring/aggregator.py` → `WEIGHTS`. Всегда должны давать сумму 1.0.

**Сигналы:**
| AI SCORE | Сигнал |
|----------|--------|
| > 60 | STRONG BUY |
| 20..60 | BUY |
| -20..20 | NEUTRAL |
| -60..-20 | SELL |
| < -60 | STRONG SELL |

---

## База данных (Storage)

### ORM модели (`storage/models.py`)

```
AssetDB         → таблица assets        (ticker, name, asset_type, exchange, sector)
OHLCVDataDB     → таблица ohlcv_data    (asset_id, timestamp, open, high, low, close, volume)
ScoringResultDB → таблица scoring_results (asset_id, timestamp, все 7 factor_scores, ai_score, signal)
```

### AsyncStorage API (`storage/database.py`)

```python
await storage.save_scores(results: list[ScoringResult]) → None
await storage.load_history(ticker, limit) → list[ScoringResult]
await storage.load_latest_all() → list[ScoringResult]
```

### Переключение бэкенда

```bash
DATABASE_URL=none                              # CSV → data/scores.csv
DATABASE_URL=postgresql+asyncpg://user:pass@host/db  # PostgreSQL
```

### Миграции

```bash
DATABASE_URL=postgresql+asyncpg://... alembic upgrade head
```

---

## API Endpoints (FastAPI)

Запуск: `uvicorn api.main:app --host 0.0.0.0 --port 8000`

| Метод | Путь | Описание |
|-------|------|----------|
| GET | `/scores` | Все 24 актива, последние скоры (async из storage) |
| GET | `/score/{ticker}` | Детальный скоринг + factor_scores (7 значений) |
| GET | `/history/{ticker}` | История AI SCORE из storage (`?limit=N`, фикс сериализации Timestamp/NaN) |
| GET | `/assets` | Список всех отслеживаемых активов |
| POST | `/score/refresh` | Ручной запуск цикла скоринга |
| WS | `/ws/live` | WebSocket (менеджер готов, трансляция данных — не реализована) |

Автоскоринг запускается через APScheduler каждые 15 минут в FastAPI lifespan.

---

## Tracked Assets (24 актива в `api/main.py`)

```python
TRACKED_ASSETS = [
    # US stocks (10)
    Asset(ticker="AAPL", ...), Asset(ticker="MSFT", ...),
    Asset(ticker="GOOGL", ...), Asset(ticker="AMZN", ...),
    Asset(ticker="TSLA", ...), Asset(ticker="NVDA", ...),
    Asset(ticker="META", ...), Asset(ticker="NFLX", ...),
    Asset(ticker="AMD", ...),  Asset(ticker="INTC", ...),
    # Russian stocks (8)
    Asset(ticker="SBER", ...), Asset(ticker="GAZP", ...),
    Asset(ticker="LKOH", ...), Asset(ticker="YNDX", ...),
    Asset(ticker="TCSG", ...), Asset(ticker="MGNT", ...),
    Asset(ticker="FIVE", ...), Asset(ticker="VKCO", ...),
    # Crypto (6)
    Asset(ticker="BTCUSDT", ...), Asset(ticker="ETHUSDT", ...),
    Asset(ticker="SOLUSDT", ...), Asset(ticker="BNBUSDT", ...),
    Asset(ticker="XRPUSDT", ...), Asset(ticker="DOGEUSDT", ...),
]
```

---

## Frontend (`frontend/index.html`)

Один HTML-файл, без npm, без build step.

| Элемент | Статус |
|---------|--------|
| Таблица всех активов с сортировкой | ✅ |
| Score cards (цветные значки сигналов) | ✅ |
| Автообновление каждые 60 сек | ✅ |
| Space Grotesk шрифт, чёрно-белый минимализм | ✅ |
| Sparklines (мини-графики 7 дней) | ✅ | SVG 60×24px, зелёный/красный тренд, Promise.all параллельный fetch |
| Детальная карточка актива (7 gauge-баров) | ✅ | Hash routing `#/asset/{ticker}`, gauge bars, responsive |
| График истории AI SCORE | ❌ |
| Страница Settings | ❌ |
| Mobile responsive (640px/1024px) | ❌ |

---

## Тесты

```bash
pytest tests/ -v          # Запуск всех тестов
pytest tests/test_storage.py  # 21 storage тест
```

| Файл | Тестов | Покрытие |
|------|--------|----------|
| `tests/test_scoring.py` | ~6 | Scoring agents |
| `tests/test_ingest.py` | ~4 | Ingest с mock-данными |
| `tests/test_storage.py` | 21 | CSV + PostgreSQL async |
| `tests/test_api.py` | ~4 | FastAPI endpoints |
| **Итого** | **~35** | **~30% (цель 80%)** |

---

## Что НЕ сделано (задачи для следующих сессий)

1. **OHLCV запись в БД** — таблица `ohlcv_data` создана, но ingestor'ы не пишут в неё
2. **WebSocket live feed** — менеджер есть в `api/main.py`, трансляция не реализована
3. ~~**Sparklines**~~ — ✅ DONE (SVG sparklines в таблице, fix `/history` endpoint)
4. ~~**Asset Detail страница**~~ — ✅ DONE (hash routing, 7 gauge-баров, responsive)
5. **History chart** — график AI SCORE за 1d/7d/30d
6. **Settings страница** — настройка весов, API ключи, пороги алертов
7. **Mobile responsive** — таблица не адаптирована под мобильные
8. **VPS deploy + SSL** — сейчас только Cloudflare temp tunnel
9. **Test coverage 80%+** — сейчас ~30%

Детальный план работы → см. `ROADMAP.md`
