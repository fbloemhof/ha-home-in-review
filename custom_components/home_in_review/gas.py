"""Gas for heating versus hot water and cooking (a degree-day regression).

Daily gas use is roughly ``base + k × degree days``: the base is hot water and cooking, which hardly depend on the
weather; the rest is space heating. The base is either set by the user (per day) or estimated from the month:
a straight line through (degree days, gas) per day, where the intercept is the base. The estimate is only used when
the month has enough days and enough spread in degree days, and when the result makes sense (base ≥ 0, k > 0). In
a month without heating (hardly any degree days) all gas is base.
"""
from __future__ import annotations

from statistics import fmean, pstdev

MIN_DAYS = 15
MIN_SPREAD_DD = 2.0      # standard deviation of daily degree days (°C) needed for a fit
NO_HEATING_DD = 1.0      # average degree days per day below which a month counts as "no heating"


def split(gas: list[float | None], dd: list[float | None], base_per_day: float | None = None) -> dict | None:
    """Split a month of daily gas use. Returns None when there is no usable data."""
    pairs = [(d, g) for g, d in zip(gas, dd, strict=False) if g is not None and d is not None]
    days = [g for g in gas if g is not None]
    if not days:
        return None
    total = sum(days)
    n = len(days)
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
        return _result(total, None, None, "unknown", pairs)
    mx, my = fmean(xs), fmean(ys)
    sxx = sum((x - mx) ** 2 for x in xs)
    k = sum((x - mx) * (y - my) for x, y in zip(xs, ys, strict=True)) / sxx
    b = my - k * mx
    if k <= 0 or b < 0:
        return _result(total, None, None, "unknown", pairs)
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
