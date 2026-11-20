"""Gas for heating versus hot water and cooking (a degree-day regression).

Daily gas use is roughly ``base + k × degree days``: the base is hot water and cooking, which hardly depend on the
weather; the rest is space heating. The base is either set by the user (per day) or estimated from the month:
a straight line through (degree days, gas) per day, where the intercept is the base. The estimate is only used when
the month has enough days and enough spread in degree days, when gas clearly follows the weather (R² ≥ MIN_R2; a
slight slope also comes from noise, or from colder tap water in winter in a home that only heats water with gas),
and when the result makes sense (base ≥ 0, k > 0). In a month without heating (hardly any degree days) all gas is
base. With ``hot_water_only`` (an option) all gas is hot water and cooking.
"""
from __future__ import annotations

from statistics import fmean, pstdev

MIN_DAYS = 15
MIN_SPREAD_DD = 2.0      # standard deviation of daily degree days (°C) needed for a fit
NO_HEATING_DD = 1.0      # average degree days per day below which a month counts as "no heating"
MIN_R2 = 0.3             # how clearly daily gas must follow the degree days before part of it is called heating
# Even a very well insulated home heated with gas uses about this much per °C degree day; a smaller slope comes from
# noise or from colder tap water in winter, not from space heating.
MIN_HEATING_KWH_PER_DD = 0.5
KWH_PER_UNIT = {"m³": 9.77, "kWh": 1.0, "ft³": 0.288, "MWh": 1000.0, "CCF": 28.8}


def split(gas: list[float | None], dd: list[float | None], base_per_day: float | None = None,
          hot_water_only: bool = False, unit: str = "m³", fahrenheit: bool = False,
          summer_base: float | None = None) -> dict | None:
    """Split a month of daily gas use. Returns None when there is no usable data.

    ``summer_base`` is gas per day in earlier months without heating (hot water and cooking only). It is used when
    the month itself can't show the base: too little spread in the weather, or a best-fit line that meets the axis
    below zero (heating clearly follows the weather, but the month says nothing about hot water)."""

    def fallback(reason: str) -> dict:
        if summer_base is not None and summer_base >= 0:
            return _result(total, min(summer_base * n, total), summer_base, "summer_base", pairs)
        return _result(total, None, None, reason, pairs)

    pairs = [(d, g) for g, d in zip(gas, dd, strict=False) if g is not None and d is not None]
    days = [g for g in gas if g is not None]
    if not days:
        return None
    total = sum(days)
    n = len(days)
    if hot_water_only:
        return _result(total, total, total / n, "hot_water_only", pairs)
    if base_per_day is not None:
        base = min(max(0.0, base_per_day) * n, total)
        return _result(total, base, base_per_day, "option", pairs)
    if not pairs:
        return None
    xs = [d for d, _ in pairs]
    ys = [g for _, g in pairs]
    if fmean(xs) < NO_HEATING_DD:
        return _result(total, total, total / n, "no_heating", pairs)
    if len(pairs) < MIN_DAYS or pstdev(xs) < MIN_SPREAD_DD:
        return fallback("unknown")
    mx, my = fmean(xs), fmean(ys)
    sxx = sum((x - mx) ** 2 for x in xs)
    sxy = sum((x - mx) * (y - my) for x, y in zip(xs, ys, strict=True))
    syy = sum((y - my) ** 2 for y in ys)
    k = sxy / sxx
    b = my - k * mx
    if k <= 0 or syy <= 0 or sxy * sxy / (sxx * syy) < MIN_R2:
        return _result(total, None, None, "weak", pairs)  # gas does not (clearly) rise when it is colder
    kwh_per_c_dd = k * KWH_PER_UNIT.get(unit, 9.77) * (1.8 if fahrenheit else 1.0)
    if kwh_per_c_dd < MIN_HEATING_KWH_PER_DD:
        return _result(total, None, None, "weak", pairs)
    if b < 0:  # heating clearly follows the weather, but the line says nothing about hot water
        return fallback("no_base")
    base = min(b * n, total)
    return _result(total, base, b, "estimate", pairs)


def _result(total: float, base: float | None, base_per_day: float | None, source: str, pairs) -> dict:
    dd_total = sum(d for d, _ in pairs)
    out = {"base_source": source, "degree_days": dd_total,
           "per_degree_day": total / dd_total if dd_total > 1 else None}
    if base is not None:
        heating = max(0.0, total - base)
        out.update({"hot_water": base, "heating": heating, "base_per_day": base_per_day,
                    "heating_per_degree_day": heating / dd_total if dd_total > 1 and heating > 0 else None})
    return out


def split_measured(gas_hours: dict[int, float], dhw: dict[int, float] | None, ch: dict[int, float] | None,
                   degree_days: float | None = None) -> dict | None:
    """Split gas per hour from the boiler's own status: the hours (0-1) it was making hot water (``dhw``) and heating
    the house (``ch``), as recorded by the integration's on-time sensors. Per hour:

    - both known: by on-time; an hour with gas but neither active is hot water and cooking (e.g. a gas hob);
    - only hot water known: hours with hot water go to hot water, the rest to heating;
    - only heating known: hours with heating go to heating, the rest to hot water and cooking.
    """
    if dhw is None and ch is None:
        return None
    hot = heat = 0.0
    for h, g in gas_hours.items():
        if g <= 0:
            continue
        d = (dhw or {}).get(h, 0.0) if dhw is not None else None
        c = (ch or {}).get(h, 0.0) if ch is not None else None
        if d is not None and c is not None:
            share = d / (d + c) if d + c > 0 else 1.0
        elif d is not None:
            share = 1.0 if d > 0 else 0.0
        else:
            share = 0.0 if c > 0 else 1.0
        hot += g * share
        heat += g * (1 - share)
    days = max(1.0, len(gas_hours) / 24)
    return {"base_source": "boiler", "hot_water": hot, "heating": heat, "base_per_day": hot / days,
            "heating_per_degree_day": heat / degree_days if degree_days and degree_days > 1 and heat > 0 else None}
