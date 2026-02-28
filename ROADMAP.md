# AI ALPHA PULSE — Roadmap

## ✅ Phase 1 — Skeleton (DONE)
- Project structure, ingestors, basic scorers, FastAPI stub

## ✅ Phase 2 — Data + Scoring (DONE)
- [x] Fix Yahoo Finance MultiIndex
- [x] Sentiment scorer (CCI + Williams %R + VPT)
- [x] Fundamental scorer (P/E, P/B, ROE, RevGrowth, D/E)
- [x] Alpha Vantage news ingestor
- [x] Все 7 scoring агентов с реальными данными

## ✅ Phase 3 — Backend + DB (DONE 2026-02-27)
- [x] PostgreSQL schema + Alembic migration (`alembic/versions/001_initial_schema.py`)
- [x] SQLAlchemy async ORM models (`storage/models.py`)
- [x] Async storage layer с CSV fallback (`storage/database.py`)
- [x] `DATABASE_URL=none` → CSV, иначе → PostgreSQL asyncpg
- [x] 21 storage тест (pytest-asyncio)
- [ ] Сохранение OHLCV в БД (таблица есть, ingestor не пишет)
- [ ] APScheduler (сейчас asyncio.sleep loop внутри FastAPI lifespan)
- [ ] WebSocket live feed

## ✅ Phase 4 — Frontend (DONE)
- [x] React-style dashboard + score cards + таблица + автообновление 60s
- [x] Минимализм, чёрно-белый, Space Grotesk шрифт
- [ ] Детальная карточка актива (7 gauge-баров с объяснением)
- [ ] Исторический chart AI SCORE

## ✅ Phase 5 — Testing + Deploy (DONE)
- [x] pytest coverage (scoring + storage)
- [x] Docker + docker-compose
- [x] GitHub Actions CI/CD
- [x] nginx конфиг
- [ ] Deploy VPS + SSL (постоянный URL)
