"""
Fundamental Scorer.

Оценивает фундаментальную силу компании:
1. P/E ratio (цена/прибыль) — стоимостная оценка
2. P/B ratio (цена/балансовая стоимость)
3. ROE (рентабельность капитала)
4. Revenue Growth (рост выручки)
5. Debt/Equity (долговая нагрузка)
6. Free Cash Flow Yield (FCF / Market Cap)
7. Earnings Surprise (факт vs ожидания)

Для крипто: используем proxy через ончейн-метрики или
             Market Cap / Volume ratio (NVT-like)

Все данные: yfinance .info (бесплатно)
"""
import numpy as np
import pandas as pd
from scoring.base import BaseScorer


class FundamentalScorer(BaseScorer):

    def score(self, df: pd.DataFrame,
              ticker: str | None = None,
              asset_type: str = "stock") -> float:
        try:
            if asset_type == "crypto":
                return self._crypto_fundamental(df)

            if ticker:
                fund_score = self._stock_fundamentals(ticker)
                if fund_score is not None:
                    return fund_score

            # Fallback: long-term price performance
            return self._price_momentum_proxy(df)

        except Exception as e:
            self.logger.error(f"FundamentalScorer error: {e}")
            return 0.0

    def _stock_fundamentals(self, ticker: str) -> float | None:
        """Загружаем фундаментальные данные через yfinance."""
        try:
            import yfinance as yf
            info = yf.Ticker(ticker).info
            if not info:
                return None

            scores = []

            # 1. P/E Ratio (Forward PE предпочтительнее)
            pe = info.get("forwardPE") or info.get("trailingPE")
            if pe and pe > 0 and pe < 1000:
                if pe < 10:    pe_s = 80.0   # очень дёшево
                elif pe < 15:  pe_s = 60.0   # дёшево
                elif pe < 20:  pe_s = 30.0   # справедливо
                elif pe < 30:  pe_s = 0.0    # нейтрально
                elif pe < 50:  pe_s = -30.0  # дорого
                else:          pe_s = -60.0  # очень дорого
                scores.append((pe_s, 0.20))
                self.logger.info(f"P/E={pe:.1f} → {pe_s:.0f}")

            # 2. P/B Ratio
            pb = info.get("priceToBook")
            if pb and pb > 0:
                if pb < 1.0:   pb_s = 80.0   # ниже балансовой — редкость
                elif pb < 2.0: pb_s = 50.0
                elif pb < 4.0: pb_s = 10.0
                elif pb < 8.0: pb_s = -20.0
                else:          pb_s = -50.0
                scores.append((pb_s, 0.10))

            # 3. ROE — рентабельность капитала (>15% = хорошо)
            roe = info.get("returnOnEquity")
            if roe is not None:
                roe_s = float(np.clip((roe - 0.10) * 500, -100, 100))
                scores.append((roe_s, 0.20))
                self.logger.info(f"ROE={roe:.2%} → {roe_s:.0f}")

            # 4. Revenue Growth (YoY)
            rev_growth = info.get("revenueGrowth")
            if rev_growth is not None:
                if rev_growth > 0.30:  rg_s = 90.0
                elif rev_growth > 0.15: rg_s = 60.0
                elif rev_growth > 0.05: rg_s = 30.0
                elif rev_growth > 0.0:  rg_s = 0.0
                elif rev_growth > -0.10: rg_s = -30.0
                else:                    rg_s = -70.0
                scores.append((rg_s, 0.20))
                self.logger.info(f"RevGrowth={rev_growth:.1%} → {rg_s:.0f}")

            # 5. Debt/Equity
            de = info.get("debtToEquity")
            if de is not None and de >= 0:
                if de < 30:    de_s = 70.0   # мало долга
                elif de < 80:  de_s = 30.0
                elif de < 150: de_s = -10.0
                elif de < 300: de_s = -50.0
                else:          de_s = -80.0
                scores.append((de_s, 0.15))

            # 6. Profit Margins
            margin = info.get("profitMargins")
            if margin is not None:
                if margin > 0.25:   mg_s = 80.0
                elif margin > 0.15: mg_s = 50.0
                elif margin > 0.05: mg_s = 10.0
                elif margin > 0:    mg_s = -10.0
                else:               mg_s = -60.0
                scores.append((mg_s, 0.15))

            if not scores:
                return None

            total_w = sum(w for _, w in scores)
            result  = sum(s * w for s, w in scores) / total_w
            result  = float(np.clip(result, -100, 100))
            self.logger.info(f"Fundamental (stock) total: {result:.1f}")
            return result

        except Exception as e:
            self.logger.warning(f"Stock fundamentals failed for {ticker}: {e}")
            return None

    def _crypto_fundamental(self, df: pd.DataFrame) -> float:
        """
        Для крипто используем NVT-подобный анализ:
        - Отношение цены к объёму (аналог P/E)
        - Тренд объёма (растущий объём = сеть растёт)
        - Волатильность как proxy риска
        """
        close  = df["close"].astype(float)
        volume = df["volume"].astype(float)
        if len(close) < 20:
            return 0.0

        # Price/Volume ratio trend (аналог NVT)
        pv_ratio  = close / (volume + 1e-10)
        pv_z      = self.normalize_zscore(pv_ratio, window=20)
        pv_score  = float(np.clip(-pv_z, -100, 100))  # низкий ratio = хорошо

        # Тренд объёма
        vol_trend = self.normalize_zscore(volume, window=20)

        return float(np.clip(pv_score * 0.5 + vol_trend * 0.5, -100, 100))

    def _price_momentum_proxy(self, df: pd.DataFrame) -> float:
        """Fallback: долгосрочный ценовой momentum."""
        close = df["close"].astype(float)
        if len(close) < 60:
            return 0.0
        ret_60 = (close.iloc[-1] / close.iloc[-60] - 1) * 100
        return float(np.clip(ret_60 * 1.5, -100, 100))
