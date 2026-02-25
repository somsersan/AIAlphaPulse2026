"""
Relative Strength Scorer.

Считает силу актива относительно бенчмарка:
- Акции vs S&P 500 (^GSPC)
- Крипто vs Bitcoin (BTCUSDT)

Формула:
  RS_ratio = (актив / актив[N дней назад]) / (бенчмарк / бенчмарк[N дней назад])
  RS_score  = Z-score этого отношения за последние 60 дней → [-100, +100]

RS > 1 → актив сильнее рынка → положительный скор
RS < 1 → актив слабее рынка  → отрицательный скор
"""
import numpy as np
import pandas as pd
from scoring.base import BaseScorer


class RelativeStrengthScorer(BaseScorer):

    BENCHMARKS = {
        "stock":  "^GSPC",     # S&P 500
        "crypto": "BTCUSDT",   # Bitcoin как крипто-бенчмарк
    }
    PERIODS = [5, 10, 20, 60]  # дни для расчёта RS

    def score(self, df: pd.DataFrame,
              benchmark_df: pd.DataFrame | None = None,
              asset_type: str = "stock") -> float:
        try:
            close = df["close"].astype(float)
            if len(close) < 20:
                return 0.0

            if benchmark_df is None or benchmark_df.empty:
                benchmark_df = self._fetch_benchmark(asset_type, len(close))

            if benchmark_df is None or benchmark_df.empty:
                return self._score_vs_own_history(close)

            b_close = benchmark_df["close"].astype(float)

            # Выравниваем по длине
            min_len = min(len(close), len(b_close))
            close   = close.iloc[-min_len:].reset_index(drop=True)
            b_close = b_close.iloc[-min_len:].reset_index(drop=True)

            # RS за разные периоды → средневзвешенный скор
            scores = []
            weights = [0.1, 0.2, 0.3, 0.4]  # больший вес длинным периодам
            for period, w in zip(self.PERIODS, weights):
                if len(close) <= period:
                    continue
                asset_ret     = close.iloc[-1] / close.iloc[-period] - 1
                benchmark_ret = b_close.iloc[-1] / b_close.iloc[-period] - 1
                # Относительная доходность
                rel = asset_ret - benchmark_ret
                scores.append((rel, w))

            if not scores:
                return 0.0

            total_w  = sum(w for _, w in scores)
            weighted = sum(r * w for r, w in scores) / total_w

            # Нормализация: ±10% outperformance → ±100 score
            result = float(np.clip(weighted * 1000, -100, 100))
            self.logger.info(f"RelativeStrength: {result:.1f} (vs {asset_type} benchmark)")
            return result

        except Exception as e:
            self.logger.error(f"RelativeStrengthScorer error: {e}")
            return 0.0

    def _fetch_benchmark(self, asset_type: str, periods: int) -> pd.DataFrame | None:
        try:
            import yfinance as yf
            ticker = self.BENCHMARKS.get(asset_type, "^GSPC")
            if asset_type == "crypto":
                # Binance для BTC бенчмарка
                import requests
                resp = requests.get(
                    "https://api.binance.com/api/v3/klines",
                    params={"symbol": "BTCUSDT", "interval": "1d", "limit": periods},
                    timeout=8
                )
                data = resp.json()
                df = pd.DataFrame(data, columns=[
                    "ts","open","high","low","close","volume",
                    "ct","qv","trades","tbb","tbq","ignore"
                ])
                for c in ["open","high","low","close","volume"]:
                    df[c] = df[c].astype(float)
                return df[["open","high","low","close","volume"]]
            else:
                df = yf.download(ticker, period="6mo", progress=False, auto_adjust=True)
                if isinstance(df.columns, pd.MultiIndex):
                    df.columns = [c[0].lower() for c in df.columns]
                else:
                    df.columns = [str(c).lower() for c in df.columns]
                return df[["open","high","low","close","volume"]].dropna() if not df.empty else None
        except Exception as e:
            self.logger.warning(f"Benchmark fetch failed: {e}")
            return None

    def _score_vs_own_history(self, close: pd.Series) -> float:
        """Fallback: сравниваем с 60-дневной скользящей средней."""
        if len(close) < 20:
            return 0.0
        ma60 = close.rolling(min(60, len(close))).mean().iloc[-1]
        deviation = (close.iloc[-1] - ma60) / (ma60 + 1e-10)
        return float(np.clip(deviation * 500, -100, 100))
