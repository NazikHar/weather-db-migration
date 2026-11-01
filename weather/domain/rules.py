"""Бізнес-правила предметної області (чиста логіка, без доступу до БД).

Правило «Чи варто виходити на вулицю» для варіанта 2 (стан повітря):

    варто виходити  <=>  us_epa_index <= 2  і  pm2_5 < 35.4 мкг/м³

Обґрунтування порогів:
- US EPA index: 1 = Good, 2 = Moderate, 3 = Unhealthy for sensitive groups, 4 = Unhealthy,
  5 = Very Unhealthy, 6 = Hazardous. Починаючи з 3 агентство рекомендує обмежувати
  перебування просто неба.
- PM2.5: 35.4 мкг/м³ — верхня межа категорії «Moderate» у шкалі EPA AQI
  (24-годинне середнє); далі починається «Unhealthy for sensitive groups».
  Друга умова страхує від випадків, коли індекс занижений іншими забруднювачами.
"""

from __future__ import annotations

from dataclasses import dataclass

EPA_INDEX_MAX_OK = 2          # 1 Good, 2 Moderate
PM2_5_MAX_OK = 35.4           # мкг/м³, верхня межа «Moderate» за EPA AQI


@dataclass(frozen=True)
class AirQualityReading:
    """Мінімальний зріз даних, потрібний правилу (не залежить від ORM)."""

    us_epa_index: int
    pm2_5: float


def is_safe_to_go_outside(reading: AirQualityReading) -> bool:
    """True — «так, варто виходити», False — «ні, краще залишитись удома»."""
    return reading.us_epa_index <= EPA_INDEX_MAX_OK and reading.pm2_5 < PM2_5_MAX_OK


def explain(reading: AirQualityReading) -> str:
    """Людське пояснення рішення — для консольного виводу."""
    reasons = []
    if reading.us_epa_index > EPA_INDEX_MAX_OK:
        reasons.append(f"US EPA index = {reading.us_epa_index} (> {EPA_INDEX_MAX_OK})")
    if reading.pm2_5 >= PM2_5_MAX_OK:
        reasons.append(f"PM2.5 = {reading.pm2_5:.1f} мкг/м³ (≥ {PM2_5_MAX_OK})")
    if not reasons:
        return "так — повітря чисте (EPA ≤ 2, PM2.5 < 35.4)"
    return "ні — " + "; ".join(reasons)
