"""
Insider/Funds Scorer.

Оценивает институциональный интерес и активность инсайдеров:
1. Институциональное владение (% акций у фондов)
2. Изменение институциональных позиций (рост/падение % за квартал)
3. Аномальный объём торгов (крупные игроки входят/выходят)
4. Short interest (процент акций в короткой позиции)

Источник: yfinance (.institutional_holders, .info, .major_holders)
Fallback: анализ объёма торгов через OBV (On-Balance Volume)

Формула Z-score:
  OBV = cumsum(volume * sign(close_change))
  OBV_score = Z-score OBV за последние 20 дней
"""
import numpy as np
import pandas as pd
from scoring.base import BaseScorer


class InsiderFundsScorer(BaseScorer):

    def score(self, df: pd.DataFrame, ticker: str | None = None) -> float:
        try:
            scores = []

            # 1. Институциональные данные через yfinance
            if ticker:
                inst_score = self._institutional_score(ticker)
                if inst_score is not None:
                    scores.append((inst_score, 0.5))

            # 2. OBV (On-Balance Volume) — всегда считаем
            obv_score = self._obv_score(df)
            scores.append((obv_score, 0.3))

            # 3. Volume surge — аномальный объём
            surge_score = self._volume_surge_score(df)
            scores.append((surge_score, 0.2))

            if not scores:
                return 0.0

            total_w = sum(w for _, w in scores)
            result = sum(s * w for s, w in scores) / total_w
            result = float(np.clip(result, -100, 100))
            self.logger.info(f"InsiderFunds: {result:.1f}")
            return result

        except Exception as e:
            self.logger.error(f"InsiderFundsScorer error: {e}")
            return 0.0

    def _institutional_score(self, ticker: str) -> float | None:
        """Анализируем институциональное владение."""
        try:
            import yfinance as yf
            t = yf.Ticker(ticker)
            info = t.info

            score = 0.0
            count = 0

            # % институционального владения (50-80% оптимально)
            inst_pct = info.get("institutionOwnership") or info.get("heldPercentInstitutions")
            if inst_pct is not None:
                inst_pct = float(inst_pct)
                if 0.5 <= inst_pct <= 0.8:
                    score += 60.0   # здоровый уровень
                elif inst_pct > 0.8:
                    score += 30.0   # очень высокий — риск распродаж
                elif inst_pct > 0.3:
                    score += 20.0
                else:
                    score -= 20.0   # мало институционалов — слабый интерес
                count += 1

            # Short interest — чем выше, тем хуже (если нет squeeze)
            short_pct = info.get("shortPercentOfFloat")
            if short_pct is not None:
                short_pct = float(short_pct)
                if short_pct < 0.05:
                    score += 30.0   # мало шортов — бычий знак
                elif short_pct < 0.10:
                    score += 0.0
                elif short_pct < 0.20:
                    score -= 30.0   # много шортов
                else:
                    score -= 60.0   # экстремальный short interest
                count += 1

            # Insider ownership (>5% = skin in the game)
            insider_pct = info.get("heldPercentInsiders")
            if insider_pct is not None:
                insider_pct = float(insider_pct)
                if insider_pct > 0.1:
                    score += 40.0
                elif insider_pct > 0.05:
                    score += 20.0
                elif insider_pct < 0.01:
                    score -= 10.0
                count += 1

            return float(np.clip(score / max(count, 1), -100, 100)) if count > 0 else None

        except Exception as e:
            self.logger.warning(f"Institutional data failed for {ticker}: {e}")
            return None

    def _obv_score(self, df: pd.DataFrame) -> float:
        """
        OBV (On-Balance Volume):
        OBV[i] = OBV[i-1] + volume[i]  if close[i] > close[i-1]
               = OBV[i-1] - volume[i]  if close[i] < close[i-1]

        Z-score OBV тренда за последние 20 дней.
        Растущий OBV при росте цены = институционалы покупают.
        """
        close  = df["close"].astype(float)
        volume = df["volume"].astype(float)
        if len(close) < 20:
            return 0.0

        direction = np.sign(close.diff().fillna(0))
        obv = (volume * direction).cumsum()

        # Z-score наклона OBV
        return self.normalize_zscore(obv, window=20)

    def _volume_surge_score(self, df: pd.DataFrame) -> float:
        """
        Аномальный объём: volume / moving_average_volume
        Если последние 5 дней объём значительно выше среднего → крупные игроки активны.
        """
        volume = df["volume"].astype(float)
        close  = df["close"].astype(float)
        if len(volume) < 20:
            return 0.0

        avg_vol = volume.rolling(20).mean()
        vol_ratio = volume / (avg_vol + 1e-10)
        recent_ratio = vol_ratio.iloc[-5:].mean()

        # Направление цены за последние 5 дней
        price_direction = np.sign(close.iloc[-1] - close.iloc[-5])

        # Высокий объём в направлении тренда → сигнал
        surge = (recent_ratio - 1.0) * price_direction
        return float(np.clip(surge * 50, -100, 100))
