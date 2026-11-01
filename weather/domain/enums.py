"""Перелічувані типи предметної області."""

from __future__ import annotations

import enum


class WindDirection(str, enum.Enum):
    """16 румбів компаса — значення колонки wind_direction у датасеті."""

    N = "N"
    NNE = "NNE"
    NE = "NE"
    ENE = "ENE"
    E = "E"
    ESE = "ESE"
    SE = "SE"
    SSE = "SSE"
    S = "S"
    SSW = "SSW"
    SW = "SW"
    WSW = "WSW"
    W = "W"
    WNW = "WNW"
    NW = "NW"
    NNW = "NNW"
