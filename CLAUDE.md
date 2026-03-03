# AI Alpha Pulse — Claude Code Instructions

This file is read automatically by Claude Code at session start.
Follow every rule here without exception.

---

## BRANCH WORKFLOW — MANDATORY

### Never touch main directly

NEVER commit to `main` directly.
NEVER run `git push origin main`.
NEVER run `git push --force` or `git push -f` to any shared branch.
NEVER run `git reset --hard` on a branch pushed to origin.
NEVER use `--no-verify` to skip commit hooks.

### Branch naming

Always create or switch to a feature branch before making any changes.

| Work type      | Prefix        | Example                              |
|----------------|---------------|--------------------------------------|
| New feature    | `feature/`    | `feature/add-websocket-streaming`    |
| Bug fix        | `fix/`        | `fix/trend-scorer-nan-crash`         |
| Chores/config  | `chore/`      | `chore/update-requirements`          |
| Refactoring    | `refactor/`   | `refactor/aggregator-weights-config` |
| Tests          | `test/`       | `test/add-ohlcv-write-coverage`      |
| Documentation  | `docs/`       | `docs/update-roadmap`                |

### Starting a new task

```bash
git checkout main
git pull origin main
git checkout -b feature/your-feature-name
```

---

## COMMIT WORKFLOW — MANDATORY

### Run tests before every commit

```bash
pytest tests/ -v
```

All tests must pass. Never commit with failing tests.

### Conventional Commits format

```
<type>(<scope>): <short description>
```

Valid types: `feat`, `fix`, `chore`, `refactor`, `test`, `docs`, `perf`
Scopes (optional): `scoring`, `api`, `ingest`, `storage`, `frontend`, `ci`

Examples:
- `feat(api): add websocket live feed endpoint`
- `fix(ingest): handle MOEX timeout with mock fallback`
- `test(storage): add OHLCV write coverage`
- `feat(frontend): add asset detail page with gauge bars`

### Merging to main

NEVER merge to `main` locally. Always create a PR:

```bash
git push -u origin feature/your-feature-name
gh pr create --title "feat: ..." --body "..."
```

---

## PROJECT ARCHITECTURE

AI Alpha Pulse = 7-agent multi-factor financial scoring platform.
AI SCORE range: -100 (STRONG SELL) → 0 (NEUTRAL) → +100 (STRONG BUY).

### Tech stack

- Python 3.11, FastAPI, Pydantic v2
- pandas, numpy, ta (technical analysis library)
- yfinance, requests (data sources)
- SQLAlchemy async + asyncpg, PostgreSQL (+ CSV fallback for dev)
- Alembic (DB migrations)
- pytest + pytest-asyncio (27+ tests)
- Docker + docker-compose + nginx
- GitHub Actions CI/CD

### 7 Scoring Agents

| Class                    | File                           | Weight |
|--------------------------|--------------------------------|--------|
| `TrendScorer`            | `scoring/trend.py`             | 35%    |
| `SentimentScorer`        | `scoring/sentiment.py`         | 20%    |
| `FundamentalScorer`      | `scoring/fundamental.py`       | 20%    |
| `RelativeStrengthScorer` | `scoring/relative_strength.py` | 10%    |
| `VolatilityScorer`       | `scoring/volatility.py`        | 5%     |
| `InsiderFundsScorer`     | `scoring/insider_funds.py`     | 5%     |
| `MacroScorer`            | `scoring/macro.py`             | 5%     |

Weights live in `scoring/aggregator.py` → `WEIGHTS` dict. Must always sum to 1.0.

### Key file paths

```
CLAUDE.md                    ← this file (Claude rules + project context)
STATUS.md                    ← what's implemented (read before starting work)
ROADMAP.md                   ← future tasks + backlog (read to understand next steps)

api/main.py                  ← FastAPI app, lifespan scheduler, TRACKED_ASSETS (24 assets)
scoring/aggregator.py        ← WEIGHTS, score_asset(), signal_from_score()
scoring/base.py              ← BaseScorer ABC, normalize_zscore()
scoring/<agent>.py           ← individual scorer implementations
common/models.py             ← Asset, ScoringResult Pydantic v2 models
common/logger.py             ← get_logger()
storage/database.py          ← AsyncStorage: PostgreSQL + CSV fallback, save_scores/load_history/load_latest_all
storage/models.py            ← SQLAlchemy ORM: AssetDB, OHLCVDataDB, ScoringResultDB
ingest/yahoo_finance.py      ← Yahoo Finance OHLCV + mock fallback
ingest/binance.py            ← Binance Public API + mock fallback
ingest/moex.py               ← MOEX ISS API + mock fallback
ingest/alpha_vantage.py      ← Alpha Vantage news + OHLCV
config/settings.py           ← env config (ALPHA_VANTAGE_API_KEY, etc.)
requirements.txt             ← Python dependencies
alembic/                     ← DB migrations (001_initial_schema.py)
alembic.ini                  ← Alembic config
tests/                       ← pytest suite (27+ tests, all must pass)
frontend/index.html          ← single-file static dashboard (no build step)
docker-compose.yml           ← API + nginx services
.github/workflows/ci.yml     ← pytest on push/PR to main
```

### Storage: how to switch backends

```bash
# CSV mode (development default — no DB needed)
DATABASE_URL=none python run.py

# PostgreSQL mode (production)
DATABASE_URL=postgresql+asyncpg://user:pass@localhost/aialpha python run.py

# Apply migrations to PostgreSQL
DATABASE_URL=postgresql+asyncpg://user:pass@localhost/aialpha alembic upgrade head
```

### Tracked assets (24 total in api/main.py)

- US stocks (10): AAPL, MSFT, GOOGL, AMZN, TSLA, NVDA, META, NFLX, AMD, INTC
- Russian stocks (8): SBER, GAZP, LKOH, YNDX, TCSG, MGNT, FIVE, VKCO
- Crypto (6): BTCUSDT, ETHUSDT, SOLUSDT, BNBUSDT, XRPUSDT, DOGEUSDT

### Data flow

```
ingestor.fetch(ticker) → pd.DataFrame (OHLCV)
  → score_asset(asset, df)
      → scorer.score(df) → float [-100, +100]  (×7 agents)
      → ai_score = Σ(score × weight)
      → ScoringResult(ticker, ai_score, signal, factor_scores)
  → storage.save_scores([result]) → PostgreSQL or CSV
```

---

## CODE STYLE

### Python rules

- Type hints required on all function signatures
- Never use bare `except:` — always `except Exception as e:`
- New scorers must inherit from `BaseScorer` (`scoring/base.py`)
- Use `self.logger = get_logger(self.__class__.__name__)` in classes
- Use `normalize_zscore()` from `BaseScorer` for signal normalization
- Use `np.clip(value, -100, 100)` on all final scorer outputs
- Register new scorers in `scoring/aggregator.py` with weight (must sum to 1.0)

### Test rules

- Every new scorer/ingestor needs tests in `tests/`
- No live network calls in tests — use `_mock_data()` pattern
- Check: return type is float, value in [-100, 100], directional correctness
- Storage tests: always use `DATABASE_URL=none` (CSV mode, no DB needed)

### Frontend (current)

- Single `frontend/index.html` — no npm, no build step (until React migration task)
- Space Grotesk font, black/white minimalist style
- Signal colors: STRONG BUY #22C55E | BUY #86EFAC | NEUTRAL #FBBF24 | SELL #FCA5A5 | STRONG SELL #EF4444
- Auto-refresh via `setInterval` polling `/scores` every 60s

---

## SAFE OPERATIONS SUMMARY

| Action                        | Allowed |
|-------------------------------|---------|
| Commit to feature branch      | YES     |
| Push feature branch to origin | YES     |
| Create PR via `gh pr create`  | YES     |
| Run `pytest tests/ -v`        | YES     |
| Commit directly to main       | NO      |
| Push to main                  | NO      |
| `git push --force`            | NO      |
| `git reset --hard` (shared)   | NO      |
| `git commit --no-verify`      | NO      |
| Merge to main locally         | NO      |
