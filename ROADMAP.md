# AI ALPHA PULSE — Roadmap + Backlog

_Обновлено: 2026-03-03 | Текущий статус: v0.4.2_

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

### 4.1 Sparklines в таблице ✅ DONE (2026-03-03)

**Реализовано в `frontend/index.html` + `api/main.py`:**
- SVG sparkline 60×24px, чистый SVG без библиотек
- Параллельный `Promise.all` fetch `GET /history/{ticker}?limit=7` для всех 24 активов
- Цвет линии: зелёный если тренд вверх, красный если вниз; "—" при < 2 точек
- Обновляется вместе с основным auto-refresh (60s)
- Исправлен endpoint `/history`: добавлен параметр `limit`, фикс сериализации `Timestamp` и `NaN` через `df.to_json(orient="records", date_format="iso")`

---

### 4.2 Asset Detail страница ✅ DONE (2026-03-02)

**Реализовано в `frontend/index.html`:**
- Hash routing `#/asset/{TICKER}` — кнопка "← Назад" возвращает на дашборд
- Тикер, название, AI SCORE (крупно), signal badge
- **7 горизонтальных gauge-баров** (−100…+100, нулевая точка по центру):
  - Положительный ≥+15: зелёный; отрицательный ≤−15: красный; нейтральный: серый
  - Подпись: "Trend (35%): +45.8" — вес берётся из `data.weights` в API-ответе
- Explanation под барами серым мелким текстом
- Responsive: desktop side-by-side, mobile stacked (`@media max-width: 700px`)

---

### 4.3 AI SCORE History Chart ✅ DONE (2026-03-03)

**Реализовано в `frontend/index.html`:**
- Переключатель периода: `1d` (limit=96) / `7d` (limit=672) / `30d` (limit=2880); активная кнопка — белая заливка; по умолчанию 7d
- SVG-график 100% ширина × 160px, чистый SVG без библиотек
- Нулевая горизонталь (пунктир серый); зелёная зона (#22C55E) выше нуля, красная (#EF4444) ниже через SVG `clipPath`
- Ось Y: метки -100 / -60 / 0 / +60 / +100 с цветовым кодированием
- Ось X: 5 равноудалённых меток; `HH:MM` для 1d, `Mon DD` для 7d/30d
- Tooltip при hover: crosshair + dot + дата/время + значение AI SCORE

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
  ✅ Phase 4.2 — Asset Detail страница (DONE 2026-03-02)
  ✅ Phase 4.1 — Sparklines (DONE 2026-03-03)
  ✅ Phase 4.3 — History Chart (DONE 2026-03-03)
  1. Phase 5.2 — OHLCV в БД (нужно для точной истории)
  2. Phase 5.4 — Docker healthchecks
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
