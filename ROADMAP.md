# AI ALPHA PULSE — Roadmap

## ✅ Phase 1 — Skeleton (DONE)
- Project structure, ingestors, basic scorers, FastAPI stub

## 🔄 Phase 2 — Data + Scoring (IN PROGRESS)
- [x] Fix Yahoo Finance MultiIndex
- [ ] Sentiment scorer (news headlines)
- [ ] Fundamental scorer (P/E, ROE)
- [ ] Alpha Vantage news ingestor

## 📦 Phase 3 — Backend + DB
- [ ] PostgreSQL schema + migrations
- [ ] Store OHLCV + scores
- [ ] APScheduler auto-scoring every 15 min
- [ ] WebSocket live feed

## 🎨 Phase 4 — Frontend
- [ ] React dashboard + score table + charts

## 🧪 Phase 5 — Testing + Deploy
- [ ] pytest >80% coverage
- [ ] Docker + docker-compose
- [ ] GitHub Actions CI/CD
- [ ] Deploy VPS + nginx + SSL
