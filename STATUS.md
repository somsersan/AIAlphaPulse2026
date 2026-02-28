# AI ALPHA PULSE — Product Status
_Последнее обновление: 2026-02-27 Phase 3 (PostgreSQL storage)_

## Версия: v0.4.0

## ✅ Что реализовано

### Ingest
- Yahoo Finance (OHLCV глобальные акции) + mock fallback
- Binance Public API (крипто реальные данные)
- MOEX ISS API (российские акции реальные данные)
- Alpha Vantage (новости + OHLCV, требует API ключ)

### Scoring — все 7 агентов
| Агент | Статус | Метод |
|-------|--------|-------|
| Trend | ✅ Реальные данные | MA20/50 crossover + RSI(14) + 5d momentum Z-score |
| Volatility | ✅ Реальные данные | ATR(14) + Bollinger Band width Z-score |
| Sentiment | ✅ Реальные данные | CCI + Williams %R + VPT + Alpha Vantage News API |
| Fundamental | ✅ Реальные данные | P/E, P/B, ROE, RevGrowth, D/E, Margins (yfinance) |
| Relative Strength | ✅ Реальные данные | Актив vs S&P500/BTC за 5/10/20/60 дней |
| Insider/Funds | ✅ Реальные данные | OBV + Volume Surge + институц. владение |
| Macro | ✅ Реальные данные | VIX + DXY + 10Y TNX + S&P500 тренд |

### AI SCORE
- Взвешенная сумма 7 агентов: Trend 35% | Sentiment 20% | Fundamental 20% | RS 10% | Volatility 5% | Insider 5% | Macro 5%
- Диапазон: -100 (STRONG SELL) → +100 (STRONG BUY)

### Storage (Phase 3 — DONE 2026-02-27)
- **`storage/models.py`** — SQLAlchemy ORM: `assets`, `ohlcv_data`, `scoring_results`
- **`storage/database.py`** — async (asyncpg) + CSV fallback по `DATABASE_URL`
  - `DATABASE_URL=none` → CSV (`data/scores.csv`)
  - `DATABASE_URL=postgresql://...` → PostgreSQL async upsert
  - Публичный API: `save_scores`, `load_history`, `load_latest_all` (все async)
- **Alembic**: `alembic.ini`, `alembic/env.py` (async), `alembic/versions/001_initial_schema.py`
  - Применить: `DATABASE_URL=postgresql://... alembic upgrade head`
- **`requirements.txt`**: добавлены `sqlalchemy[asyncio]>=2.0`, `alembic>=1.13`, `asyncpg>=0.29`, `greenlet>=3.0`, `pytest-asyncio>=0.23`
- **21 тест**, все проходят (`pytest tests/test_storage.py`)

### API (FastAPI)
- GET /score/{ticker} — полный скоринг + factor_scores (7 значений)
- GET /scores — все активы (async)
- GET /history/{ticker} — история (async)
- GET /assets — список
- POST /score/refresh — ручной запуск цикла
- Автоскоринг каждые 15 мин

### Frontend
- Дашборд: карточки + таблица + автообновление 60s
- Минимализм, чёрно-белый, Space Grotesk

### Deploy
- Dockerfile + docker-compose + nginx
- GitHub Actions CI/CD

## ❌ В разработке / не готово
1. Детальная карточка актива (клик → 7 факторов с объяснением)
2. График истории AI SCORE
3. Постоянный URL (сейчас Cloudflare temp tunnel)
4. Сохранение OHLCV данных в БД (таблица `ohlcv_data` создана, но ingestor не пишет в неё)
5. WebSocket live feed

## 🔄 Следующий этап
- Детальная карточка в UI с 7 gauge-барами
- Исторический chart AI SCORE
- Запись OHLCV в БД через ingestor
