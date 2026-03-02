# AI ALPHA PULSE — Roadmap + Backlog

_Обновлено: 2026-03-02 | Текущий статус: v0.4.0_

---

## Статус фаз

| Фаза | Название | Статус |
|------|----------|--------|
| Phase 1 | Skeleton (структура, ingestors, FastAPI) | ✅ DONE |
| Phase 2 | Data + Scoring (все 7 агентов) | ✅ DONE |
| Phase 3 | Backend + DB (PostgreSQL, Alembic, async) | ✅ DONE |
| Phase 4 | Frontend improvements | 🔄 IN PROGRESS |
| Phase 5 | Testing + Deploy | 🔄 IN PROGRESS |
| Phase 6 | Advanced Features | ⏳ BACKLOG |
| Phase 7 | Monetization | ⏳ BACKLOG |

---

## Phase 4 — Frontend Improvements (текущий приоритет)

Базовый дашборд уже есть (`frontend/index.html`). Нужно добавить детальность и интерактивность.

### 4.1 Sparklines в таблице

**Задача:** Мини-графики истории AI SCORE (7 дней) в каждой строке таблицы.

**Подзадачи:**
- Загружать `GET /history/{ticker}?limit=7` для каждого актива при загрузке страницы
- Рисовать SVG sparkline (40×20px) прямо в `<td>` — без библиотек, чистый SVG
- Цвет линии: зелёный если тренд вверх, красный если вниз
- Обновлять вместе с основным auto-refresh (60s)

**Примечание:** Для sparklines нужны данные в `storage` (история). Убедиться что scheduler действительно пишет каждые 15 мин.

**Файлы:** `frontend/index.html`, `api/main.py` (endpoint /history уже есть)

---

### 4.2 Asset Detail страница

**Задача:** По клику на тикер → детальная страница с полным анализом.

**Подзадачи:**
- Роутинг через `#/asset/AAPL` (hash-routing, без серверного роутера)
- Показывать: тикер, название, текущий AI SCORE (большой), сигнал
- **7 gauge-баров** — один на каждый фактор:
  - Горизонтальный прогресс-бар от -100 до +100
  - Цвет: красный (отрицательный) → серый (нейтральный) → зелёный (положительный)
  - Подпись: название фактора + числовое значение + вес (35%, 20%, и т.д.)
- **NL объяснения** для каждого фактора — брать из `ScoringResult.explanation` (поле уже есть в Pydantic модели)
- Кнопка "← Назад" на дашборд

**API:** `GET /score/{ticker}` уже возвращает `factor_scores` — использовать его.

**Файлы:** `frontend/index.html`, `common/models.py` (проверить поле explanation)

---

### 4.3 AI SCORE History Chart

**Задача:** Линейный график истории AI SCORE на странице детали актива.

**Подзадачи:**
- Переключатель периода: 1d / 7d / 30d (кнопки)
- Загружать `GET /history/{ticker}?limit=N` где N = 96 (1d×15min), 672 (7d), 2880 (30d)
- Рисовать SVG путь (path) — чистый SVG без библиотек
- Ось X: метки времени (часы для 1d, дни для 7d/30d)
- Ось Y: от -100 до +100, нулевая линия подсвечена
- Tooltip при hover на точку: дата + AI SCORE

**Файлы:** `frontend/index.html`, `api/main.py` (проверить параметры endpoint /history)

---

### 4.4 Mobile Responsive

**Задача:** Адаптация под экраны 320px-640px и 640px-1024px.

**Подзадачи:**
- Breakpoint 640px: таблица → карточки (каждый актив = карточка)
- Breakpoint 1024px: убрать лишние колонки (оставить тикер, AI SCORE, сигнал, sparkline)
- Gauge-бары на детальной странице — полная ширина на мобильном
- Протестировать в Chrome DevTools (Mobile view)

**Файлы:** `frontend/index.html` (CSS media queries)

---

### 4.5 WebSocket Live Feed

**Задача:** Реал-тайм обновления без polling (замена `setInterval`).

**Подзадачи:**
- В `api/main.py` WebSocketManager уже есть — добавить трансляцию данных после каждого цикла скоринга
- В scheduler'е после `save_scores()` вызывать `ws_manager.broadcast(latest_scores_json)`
- На фронтенде: заменить `setInterval` на `WebSocket` с reconnect логикой
- При разрыве соединения — fallback на polling каждые 60s

**Файлы:** `api/main.py` (WebSocketManager), `frontend/index.html`

---

## Phase 5 — Testing + Deploy (текущий приоритет)

### 5.1 Покрытие тестов до 80%+

**Задача:** Расширить pytest-suite с ~30% до 80%+.

**Подзадачи:**
- `tests/test_scoring.py`: добавить тесты для каждого агента с bullish/bearish mock data
  - TrendScorer: bullish (MA20 > MA50, RSI 60), bearish (death cross, RSI 30)
  - SentimentScorer, FundamentalScorer, RelativeStrengthScorer
  - VolatilityScorer, InsiderFundsScorer, MacroScorer
- `tests/test_ingest.py`: покрыть Binance, MOEX, Alpha Vantage
- `tests/test_api.py`: покрыть все endpoints + edge cases (неизвестный тикер, пустая история)
- Добавить `tests/test_aggregator.py`: проверить что веса = 1.0, signal_from_score() граничные значения
- Запускать: `pytest tests/ --cov=. --cov-report=term-missing`

**Файлы:** `tests/` (все файлы)

---

### 5.2 OHLCV запись в БД

**Задача:** ingestor'ы должны писать OHLCV данные в таблицу `ohlcv_data`.

**Подзадачи:**
- В `storage/database.py` добавить метод `save_ohlcv(ticker, df: pd.DataFrame)`
- В `api/main.py` в цикле скоринга: после `ingestor.fetch()` → `await storage.save_ohlcv(ticker, df)`
- Дедупликация по `UNIQUE(asset_id, timestamp)` — ON CONFLICT DO NOTHING
- Добавить тест в `tests/test_storage.py`

**Файлы:** `storage/database.py`, `api/main.py`

---

### 5.3 VPS Deploy + SSL

**Задача:** Постоянный URL с HTTPS вместо Cloudflare tunnel.

**Подзадачи:**
- Арендовать VPS: Hetzner CX22 (~6€/мес) или DigitalOcean Droplet ($6/мес)
- Зарегистрировать домен (.com, ~$10/год)
- Настроить nginx для SSL: `certbot --nginx -d yourdomain.com`
- Создать `.env` файл на сервере с production переменными
- Запустить `docker-compose up -d`
- Настроить автоперезапуск: `docker-compose restart` или systemd unit

**Файлы:** `docker-compose.yml` (проверить healthchecks), `nginx.conf` (SSL секция)

---

### 5.4 Docker + PostgreSQL Healthchecks

**Задача:** PostgreSQL должен быть healthy перед стартом API сервиса.

**Подзадачи:**
- В `docker-compose.yml` добавить healthcheck для postgres сервиса
- API сервис: добавить `depends_on: postgres: {condition: service_healthy}`
- Протестировать: `docker-compose up` — API не должен падать пока postgres не готов

**Файлы:** `docker-compose.yml`

---

## Phase 6 — Advanced Features (после MVP deploy)

### 6.1 Telegram Alerts

**Задача:** Уведомление при смене сигнала (BUY→SELL или SELL→BUY).

**Подзадачи:**
- Создать `alerts/telegram.py` с ботом через python-telegram-bot
- В scheduler'е: сравнивать новый сигнал с предыдущим из storage → при смене отправлять сообщение
- Конфиг: `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID` в `.env`
- Формат сообщения: "🔄 AAPL: BUY → SELL | AI SCORE: 45 → -15 | 2026-03-02 14:00"
- Поддержка подписки на конкретные тикеры (список в `.env`)

**Файлы:** новый `alerts/telegram.py`, `scheduler.py`, `config/settings.py`

---

### 6.2 Backtesting Engine

**Задача:** Проверить исторически насколько сигналы были прибыльны.

**Подзадачи:**
- Скачать историю OHLCV за 1-3 года (yfinance)
- Запустить всех 7 агентов на исторических данных (скользящее окно)
- Симулировать сделки: BUY при score > 60, SELL при score < -60
- Метрики: Total Return, Sharpe Ratio, Max Drawdown, Win Rate
- Визуализация: Plotly (equity curve, drawdown chart)
- Сравнение с buy-and-hold бенчмарком

**Файлы:** новый `backtesting/engine.py`, `backtesting/visualize.py`

---

### 6.3 ML-оптимизация весов

**Задача:** Автоматически подбирать веса агентов для максимизации доходности.

**Подзадачи:**
- Использовать backtesting engine как objective function
- Оптимизатор: scipy.optimize или scikit-learn (GridSearch)
- Разные веса для разных режимов рынка (bull/bear/sideways)
- Детекция режима: S&P500 vs MA200, VIX уровень
- Сохранять оптимальные веса в конфиг

**Файлы:** новый `ml/weight_optimizer.py`, обновить `scoring/aggregator.py`

---

### 6.4 Portfolio Scoring

**Задача:** Оценка всего портфеля (набора активов) как единого целого.

**Подзадачи:**
- Endpoint: `POST /portfolio/score` с телом `{positions: [{ticker, weight}, ...]}`
- Взвешенный средний AI SCORE по позициям
- Анализ диверсификации: корреляционная матрица факторов
- Рекомендации: какие позиции "тянут" портфель вниз

**Файлы:** новый `api/portfolio.py`, `scoring/portfolio_scorer.py`

---

## Phase 7 — Monetization (опционально, после MVP)

### 7.1 JWT Auth + User Management

**Задача:** Регистрация/логин пользователей.

**Подзадачи:**
- `POST /auth/register`, `POST /auth/login` → JWT токен
- Middleware для проверки токена на protected endpoints
- User модель в PostgreSQL (`users` таблица)
- Библиотека: python-jose + passlib

**Файлы:** новый `api/auth.py`, новая `alembic/versions/002_add_users.py`

---

### 7.2 Stripe Subscription (Free/Pro тиры)

**Задача:** Монетизация через подписку.

**Подзадачи:**
- Free: 5 активов, задержка 15 мин, базовые факторы
- Pro ($19/мес): 24+ активов, real-time, все факторы, alerts
- Stripe Checkout для оплаты
- Webhook для обработки событий подписки

**Файлы:** новый `api/billing.py`

---

### 7.3 Rate Limiting

**Задача:** Ограничение запросов по тиру.

**Подзадачи:**
- slowapi (FastAPI rate limiter) — X req/min в зависимости от тира
- Free: 10 req/min | Pro: 100 req/min | API: 1000 req/min

**Файлы:** `api/main.py`

---

### 7.4 Email Notifications

**Задача:** Еженедельный дайджест сигналов на email.

**Подзадачи:**
- Топ-5 BUY и Топ-5 SELL за неделю
- SMTP через Resend или AWS SES
- Шаблон HTML письма
- Расписание: каждое воскресенье 18:00

**Файлы:** новый `alerts/email.py`

---

## Backlog (дополнительные фичи)

Идеи для реализации по желанию, в любом порядке:

| # | Фича | Сложность | Ценность |
|---|------|-----------|---------|
| 1 | Кастомные вотчлисты (пользователь добавляет свои тикеры) | Medium | High |
| 2 | Сравнение двух активов side-by-side | Low | High |
| 3 | Детекция рыночного режима (bull/bear/sideways) | Medium | High |
| 4 | Новостная лента (Alpha Vantage + RSS) с тегами по тикерам | Medium | Medium |
| 5 | Корреляционная матрица активов (тепловая карта) | Medium | Medium |
| 6 | Секторный анализ (средний AI SCORE по секторам) | Low | Medium |
| 7 | CSV/Excel экспорт данных скоринга | Low | Medium |
| 8 | Earnings calendar интеграция (предупреждение перед отчётом) | High | High |
| 9 | RSI дивергенция как отдельный сигнал | Medium | Medium |
| 10 | Dark mode (CSS переключатель) | Low | Low |
| 11 | Discord webhook алерты (как альтернатива Telegram) | Low | Medium |
| 12 | API playground в UI (Swagger-like для пользователей) | High | Low |
| 13 | Публичный профиль (поделиться своим вотчлистом) | High | Low |
| 14 | On-chain метрики для крипто (Glassnode/CryptoQuant API) | High | High |
| 15 | Sentiment из Twitter/Reddit (при наличии API) | High | Medium |

---

## Порядок работы (рекомендация)

```
Текущий приоритет:
  1. Phase 4.2 — Asset Detail страница (самый заметный UX win)
  2. Phase 4.1 — Sparklines
  3. Phase 5.2 — OHLCV в БД (нужно для sparklines и charts)
  4. Phase 4.3 — History Chart
  5. Phase 5.4 — Docker healthchecks
  6. Phase 5.3 — VPS Deploy + SSL  ← MVP milestone
  7. Phase 4.4 — Mobile Responsive
  8. Phase 4.5 — WebSocket
  9. Phase 5.1 — Test coverage 80%+

После MVP:
  Phase 6.1 → Telegram Alerts
  Phase 6.2 → Backtesting
```

---

## Оценка затрат (оставшееся)

| Блок | Сессий Claude Code | Стоимость |
|------|-------------------|-----------|
| Phase 4 (оставшееся) | 4–5 | ~$8–18 |
| Phase 5 (оставшееся) | 3–4 | ~$6–14 |
| Phase 6 Advanced | 10–12 | ~$20–42 |
| Phase 7 Monetization | 5–6 | ~$10–21 |
| **MVP (4+5)** | **7–9** | **~$14–32** |
| **Полный продукт** | **22–27** | **~$44–95** |
