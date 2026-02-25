"""
Macro Scorer.

Оценивает макроэкономический контекст:
1. VIX (индекс страха) — высокий VIX = риск-офф = негативно для акций
2. DXY (индекс доллара) — сильный доллар = давление на активы
3. 10Y Treasury Yield (^TNX) — рост ставок = давление на акции роста
4. S&P 500 тренд (^GSPC) — общий рыночный режим

Данные: yfinance (всё бесплатно, публично)

Формула:
  Каждый макрофактор нормализуется через Z-score за 60 дней.
  Итоговый Macro Score = взвешенная сумма с учётом типа актива.

Для крипто: VIX и DXY менее значимы, важнее BTC dominance proxy.
"""
import numpy as np
import pandas as pd
from scoring.base import BaseScorer


class MacroScorer(BaseScorer):

    MACRO_TICKERS = {
        "vix":   "^VIX",    # Volatility Index
        "dxy":   "DX-Y.NYB", # US Dollar Index
        "tnx":   "^TNX",    # 10Y Treasury Yield
        "sp500": "^GSPC",   # S&P 500
    }

    def score(self, df: pd.DataFrame, asset_type: str = "stock") -> float:
        try:
            macro_data = self._fetch_macro_data()
            if not macro_data:
                self.logger.warning("No macro data available, using market regime proxy")
                return self._market_regime_from_df(df)

            scores = []

            # 1. VIX — инвертированный (низкий VIX = хорошо)
            if "vix" in macro_data:
                vix_score = self._vix_score(macro_data["vix"])
                weight = 0.35 if asset_type == "stock" else 0.2
                scores.append((vix_score, weight))
                self.logger.info(f"VIX score: {vix_score:.1f}")

            # 2. DXY — для акций сильный доллар плохо, для крипто нейтрально
            if "dxy" in macro_data and asset_type == "stock":
                dxy_score = self._dxy_score(macro_data["dxy"])
                scores.append((dxy_score, 0.20))
                self.logger.info(f"DXY score: {dxy_score:.1f}")

            # 3. 10Y Yield — рост ставок = давление на акции роста
            if "tnx" in macro_data and asset_type == "stock":
                tnx_score = self._tnx_score(macro_data["tnx"])
                scores.append((tnx_score, 0.25))
                self.logger.info(f"TNX score: {tnx_score:.1f}")

            # 4. S&P 500 тренд — общий риск-аппетит
            if "sp500" in macro_data:
                sp_score  = self._trend_score_simple(macro_data["sp500"])
                weight = 0.20 if asset_type == "stock" else 0.40
                scores.append((sp_score, weight))
                self.logger.info(f"SP500 trend score: {sp_score:.1f}")

            if not scores:
                return 0.0

            total_w = sum(w for _, w in scores)
            result  = sum(s * w for s, w in scores) / total_w
            result  = float(np.clip(result, -100, 100))
            self.logger.info(f"MacroScore: {result:.1f} (asset_type={asset_type})")
            return result

        except Exception as e:
            self.logger.error(f"MacroScorer error: {e}")
            return 0.0

    def _fetch_macro_data(self) -> dict[str, pd.Series]:
        """Загружаем макро-данные через yfinance."""
        import yfinance as yf
        result = {}
        for name, ticker in self.MACRO_TICKERS.items():
            try:
                df = yf.download(ticker, period="6mo", progress=False, auto_adjust=True)
                if df.empty:
                    continue
                if isinstance(df.columns, pd.MultiIndex):
                    df.columns = [c[0].lower() for c in df.columns]
                else:
                    df.columns = [str(c).lower() for c in df.columns]
                result[name] = df["close"].dropna()
                self.logger.info(f"Macro {ticker}: {len(result[name])} points")
            except Exception as e:
                self.logger.warning(f"Failed to fetch {ticker}: {e}")
        return result

    def _vix_score(self, vix: pd.Series) -> float:
        """
        VIX < 15: низкий страх → рынок спокойный → +70
        VIX 15-20: нормально → +20
        VIX 20-30: повышенный → -30
        VIX > 30: паника → -80
        VIX > 40: экстремальная паника → -100
        """
        current = vix.iloc[-1]
        trend   = vix.iloc[-1] - vix.iloc[-20:].mean()  # выше/ниже 20-дневной средней

        if current < 15:   base = 70.0
        elif current < 20: base = 20.0
        elif current < 25: base = -20.0
        elif current < 30: base = -50.0
        elif current < 40: base = -75.0
        else:              base = -100.0

        # Корректируем на тренд VIX (растущий VIX хуже)
        trend_adj = float(np.clip(-trend * 5, -20, 20))
        return float(np.clip(base + trend_adj, -100, 100))

    def _dxy_score(self, dxy: pd.Series) -> float:
        """
        Сильный доллар (DXY растёт) = давление на commodities и non-US акции.
        Z-score 20-дневного изменения DXY, инвертированный.
        """
        z = self.normalize_zscore(dxy.pct_change(5), window=60)
        return float(np.clip(-z, -100, 100))  # инвертируем

    def _tnx_score(self, tnx: pd.Series) -> float:
        """
        10Y yield > 5%: плохо для акций роста
        Резкий рост ставок → негативно
        """
        current = tnx.iloc[-1]
        change_20d = tnx.iloc[-1] - tnx.iloc[-20]

        if current < 2.0:   level_score = 80.0
        elif current < 3.0: level_score = 40.0
        elif current < 4.0: level_score = 0.0
        elif current < 5.0: level_score = -40.0
        else:               level_score = -80.0

        trend_adj = float(np.clip(-change_20d * 20, -30, 30))
        return float(np.clip(level_score + trend_adj, -100, 100))

    def _trend_score_simple(self, prices: pd.Series) -> float:
        """MA20 vs MA50 + 20-дневный momentum."""
        if len(prices) < 50:
            return 0.0
        ma20 = prices.rolling(20).mean().iloc[-1]
        ma50 = prices.rolling(50).mean().iloc[-1]
        momentum = prices.pct_change(20).iloc[-1]
        ma_signal = 1.0 if ma20 > ma50 else -1.0
        return float(np.clip(ma_signal * 50 + momentum * 300, -100, 100))

    def _market_regime_from_df(self, df: pd.DataFrame) -> float:
        """Fallback: оцениваем рыночный режим по самому активу."""
        close = df["close"].astype(float)
        if len(close) < 20:
            return 0.0
        return self.normalize_zscore(close.pct_change(10), window=60)
