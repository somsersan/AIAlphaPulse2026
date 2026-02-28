# AI ALPHA PULSE — Claude Session Memory
_Актуально на: 2026-02-27_

## Проект
AI ALPHA PULSE — финансовый дашборд с 7-факторным скорингом активов.
Рабочая директория: `/Users/semenisaev/AIAlphaPulse2026`
Активная ветка worktree: `claude/confident-ramanujan`

## Текущая версия: v0.4.0

## Ключевые файлы
```
storage/models.py        — SQLAlchemy ORM (assets, ohlcv_data, scoring_results)
storage/database.py      — async storage layer (asyncpg + CSV fallback)
alembic/                 — миграции (001_initial_schema.py готова)
alembic.ini              — конфиг Alembic
api/main.py              — FastAPI, все storage-вызовы теперь async/await
common/models.py         — Pydantic: Asset, ScoringResult (factor_scores: dict)
tests/test_storage.py    — 21 тест (CSV helpers + async API + PG mock)
pytest.ini               — asyncio_mode = auto
STATUS.md                — детальный статус проекта
ROADMAP.md               — роадмап с отметками выполненного
```

## Архитектурные решения

### Storage backend switch
```python
DATABASE_URL=none        → CSV fallback (data/scores.csv)
DATABASE_URL=postgresql://... → asyncpg + SQLAlchemy async
```
`USE_POSTGRES` определяется при импорте модуля по `os.getenv("DATABASE_URL")`.

### Публичный API storage (все async)
- `save_scores(results)` — upsert, пустой список игнорируется
- `load_history(ticker, days)` → pd.DataFrame
- `load_latest_all()` → pd.DataFrame
- `init_db()` — create_all (для dev без Alembic)

### factor_scores в ScoringResult
`ScoringResult.factor_scores` — dict с ключами:
`sentiment`, `fundamental`, `relative_strength`, `insider_funds`, `macro`
(плюс `trend_score`, `volatility_score` как отдельные поля модели)

### Alembic (async)
`alembic/env.py` переопределяет `sqlalchemy.url` из `DATABASE_URL` env var.
Запуск: `DATABASE_URL=postgresql://... alembic upgrade head`

## Что НЕ сделано (следующие итерации)
- Запись OHLCV в БД через ingestor (таблица `ohlcv_data` создана, но не используется)
- Детальная карточка UI с 7 gauge-барами
- Исторический chart AI SCORE
- WebSocket live feed
- Постоянный VPS deploy + SSL

## Зависимости (requirements.txt)
sqlalchemy[asyncio]>=2.0, alembic>=1.13, asyncpg>=0.29, greenlet>=3.0, pytest-asyncio>=0.23
+ yfinance, pandas, numpy, fastapi, uvicorn, pydantic, ta, python-dotenv, requests

## Тесты
```bash
DATABASE_URL=none python -m pytest tests/test_storage.py -v   # 21/21 passed
python -m pytest tests/ -v                                     # все тесты
```
