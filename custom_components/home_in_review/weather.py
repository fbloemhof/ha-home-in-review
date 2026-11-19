"""Outdoor weather from Open-Meteo (no API key, worldwide, with history).

Only a coarsened location is sent (0.1°, about 10 km): the ERA5 reanalysis grid is 0.25°, so more
precision would add nothing but would reveal the home location.

- daily(): observed (reanalysis) daily values for a period. ERA5 lags ~5 days; the last days of a month are
  filled from the forecast API, which serves recent past days.
- normals(): 1991-2020 monthly climate normals for the location, computed once and cached.
"""
from __future__ import annotations

import datetime as dt
from urllib.parse import urlencode

ARCHIVE = "https://archive-api.open-meteo.com/v1/archive"
FORECAST = "https://api.open-meteo.com/v1/forecast"
DAILY = "temperature_2m_mean,temperature_2m_min,temperature_2m_max,precipitation_sum,sunshine_duration"
NORMALS_VERSION = 1


def coarse(x: float) -> float:
    """The location as sent to Open-Meteo: rounded to 0.1° (about 10 km)."""
    return round(float(x), 1)


_coarse = coarse


def _rows(js: dict) -> list[dict]:
    d = js.get("daily") or {}
    out = []
    for i, day in enumerate(d.get("time", [])):
        out.append({
            "d": day,
            "mean": d["temperature_2m_mean"][i],
            "min": d["temperature_2m_min"][i],
            "max": d["temperature_2m_max"][i],
            "precip": d["precipitation_sum"][i],
            "sun_h": (d["sunshine_duration"][i] / 3600) if d["sunshine_duration"][i] is not None else None,
        })
    return out


async def daily(src, lat: float, lon: float, first: dt.date, last: dt.date, tz: str) -> list[dict]:
    q = {"latitude": _coarse(lat), "longitude": _coarse(lon), "start_date": first.isoformat(),
         "end_date": last.isoformat(), "daily": DAILY, "timezone": tz}
    rows = _rows(await src.fetch_json(f"{ARCHIVE}?{urlencode(q)}"))
    missing = [r["d"] for r in rows if r["mean"] is None]
    if missing and dt.date.fromisoformat(missing[0]) > dt.date.today() - dt.timedelta(days=90):
        q.update(start_date=missing[0], end_date=missing[-1])
        recent = {r["d"]: r for r in _rows(await src.fetch_json(f"{FORECAST}?{urlencode(q)}"))}
        rows = [recent.get(r["d"], r) if r["mean"] is None else r for r in rows]
    return rows


async def normals(src, lat: float, lon: float, cache: dict) -> list[dict] | None:
    """Monthly 1991-2020 means: [{"temp", "precip", "sun_h"}] for January..December."""
    key = f"normals_v{NORMALS_VERSION}_{_coarse(lat)}_{_coarse(lon)}"
    if key in cache:
        return cache[key]
    q = {"latitude": _coarse(lat), "longitude": _coarse(lon), "start_date": "1991-01-01",
         "end_date": "2020-12-31", "daily": "temperature_2m_mean,precipitation_sum,sunshine_duration",
         "timezone": "GMT"}
    js = await src.fetch_json(f"{ARCHIVE}?{urlencode(q)}")
    d = js.get("daily") or {}
    acc = [{"t": [], "p": 0.0, "s": 0.0, "n": 0} for _ in range(12)]
    for i, day in enumerate(d.get("time", [])):
        m = int(day[5:7]) - 1
        if d["temperature_2m_mean"][i] is not None:
            acc[m]["t"].append(d["temperature_2m_mean"][i])
        acc[m]["p"] += d["precipitation_sum"][i] or 0
        acc[m]["s"] += (d["sunshine_duration"][i] or 0) / 3600
    years = 30
    out = [{"temp": sum(a["t"]) / len(a["t"]) if a["t"] else None, "precip": a["p"] / years, "sun_h": a["s"] / years}
           for a in acc]
    cache[key] = out
    return out


# Dutch "gewogen graaddagen", the usual weighting for comparing gas use: November-February count more, April-September less.
NL_WEIGHTS = {1: 1.1, 2: 1.1, 3: 1.0, 4: 0.8, 5: 0.8, 6: 0.8, 7: 0.8, 8: 0.8, 9: 0.8, 10: 1.0, 11: 1.1, 12: 1.1}


def dd_settings(metric: bool, base: float | None, weighted: bool) -> tuple[float, bool]:
    """The heating threshold in the display unit (18 °C / 65 °F unless set) and whether to weight by month."""
    if base is None:
        base = 18.0 if metric else 65.0
    return float(base), bool(weighted)


def degree_days(mean: float | None, month: int, base: float, weighted: bool) -> float | None:
    """Heating degree days of one day, in the unit of ``mean`` and ``base``."""
    if mean is None:
        return None
    return max(0.0, base - mean) * (NL_WEIGHTS[month] if weighted else 1.0)


def summarize(days: list[dict], normals: list[dict] | None, month: int, metric: bool,
              dd_base: float | None = None, dd_weighted: bool = False) -> dict:
    """Month statistics. Temperatures are °C internally and converted at the end when not metric."""
    means = [d["mean"] for d in days if d["mean"] is not None]
    if not means:
        return {}
    lows = [d["min"] for d in days if d["min"] is not None]
    highs = [d["max"] for d in days if d["max"] is not None]
    # Degree days are computed in the display unit, with the user's threshold (default 18 °C / 65 °F).
    base, weighted = dd_settings(metric, dd_base, dd_weighted)
    to_disp = (lambda c: c) if metric else (lambda c: c * 9 / 5 + 32)
    out = {
        "temp": sum(means) / len(means),
        "min": min(lows) if lows else None,
        "max": max(highs) if highs else None,
        "frost_days": sum(1 for x in lows if x < 0),
        "summer_days": sum(1 for x in highs if x >= 25),
        "degree_days": sum(degree_days(to_disp(x), month, base, weighted) for x in means),
        "dd_base": base, "dd_weighted": weighted,
        "precip": sum(d["precip"] or 0 for d in days) if any(d.get("precip") is not None for d in days) else None,
        "sun_h": sum(d["sun_h"] or 0 for d in days) if any(d.get("sun_h") is not None for d in days) else None,
        "days_complete": len(means),
    }
    if normals and normals[month - 1].get("temp") is not None:
        n = normals[month - 1]
        out["normal"] = {"temp": n["temp"], "precip": n["precip"], "sun_h": n["sun_h"]}
    out["daily"] = [{"d": d["d"], "mean": d["mean"], "min": d["min"], "max": d["max"], "precip": d["precip"]} for d in days]
    if not metric:
        f = lambda c: None if c is None else c * 9 / 5 + 32  # noqa: E731
        for k in ("temp", "min", "max"):
            out[k] = f(out[k])
        if "normal" in out:
            out["normal"]["temp"] = f(out["normal"]["temp"])
        for d in out["daily"]:
            for k in ("mean", "min", "max"):
                d[k] = f(d[k])
        out["precip_unit"] = "in"
        if out["precip"] is not None:
            out["precip"] /= 25.4
        if "normal" in out:
            out["normal"]["precip"] /= 25.4
    else:
        out["precip_unit"] = "mm"
    return out
