"""Collect one month of data into a plain JSON-able report document.

This module has no Home Assistant imports: everything it needs comes from a *source* object, so the
same code runs inside Home Assistant (HassSource) and in the development runner (WebSocket source).

A source provides these coroutines:
    config() -> {"time_zone", "latitude", "longitude", "currency", "unit_system", "language"}
    energy_prefs() -> energy dashboard preferences dict, or None
    statistics_meta(ids) -> {statistic_id: {"unit": str|None, "unit_class": str|None}}
    statistics(ids, start, end, period, units, types) -> {statistic_id: [row, ...]}, row["start"] in epoch seconds
    climate_sensors() -> [{"entity_id", "name", "device_class", "area_id", "area_name", "floor_name"}]
    fetch_json(url) -> parsed JSON
"""
from __future__ import annotations

import datetime as dt
import logging
import statistics as pystats
from typing import Any
from zoneinfo import ZoneInfo

from . import weather
from .const import DEFAULT_MAX_HOURLY_KWH, OUTDOOR_AREA_HINTS, SCHEMA_VERSION

_LOGGER = logging.getLogger(__name__)

# A meter whose statistics start this long after the month start counts as "partial".
PARTIAL_GRACE_S = 2 * 86400
# A climate sensor needs this share of hourly values to count.
MIN_COVERAGE = 0.5


# ----------------------------------------------------------------------------- time helpers
def month_bounds(year: int, month: int, tz: ZoneInfo) -> tuple[dt.datetime, dt.datetime]:
    start = dt.datetime(year, month, 1, tzinfo=tz)
    end = dt.datetime(year + (month == 12), month % 12 + 1, 1, tzinfo=tz)
    return start, end


def hour_starts(start: dt.datetime, end: dt.datetime) -> list[int]:
    """Epoch seconds of every hour in [start, end). Correct across DST changes."""
    return list(range(int(start.timestamp()), int(end.timestamp()), 3600))


def is_outdoor_name(name: str) -> bool:
    n = name.lower()
    return any(h in n for h in OUTDOOR_AREA_HINTS)


def prefer_room_sensors(sensors: list[dict]) -> list[dict]:
    """Keep the temperature sensors that most likely measure the room.

    A device that reports both temperature and humidity is almost always a room climate sensor. When an area has
    one, its other temperature sensors (motion sensors, pipe probes, the chip temperature of a CO2 module) are
    dropped. Areas without such a device keep all their temperature sensors, except the temperature of a bare CO2
    module (CO2 but no humidity, e.g. MH-Z19), which reports its own chip temperature.
    """
    humid_devices = {s["device_id"] for s in sensors if s["device_class"] == "humidity" and s.get("device_id")}
    co2_only = {s["device_id"] for s in sensors if s["device_class"] == "carbon_dioxide" and s.get("device_id")} - humid_devices
    climate_areas = {s["area_id"] for s in sensors if s["device_class"] == "temperature" and s.get("device_id") in humid_devices}
    out = []
    for s in sensors:
        if s["device_class"] == "temperature":
            if s.get("device_id") in co2_only:
                continue
            if s["area_id"] in climate_areas and s.get("device_id") not in humid_devices:
                continue
        out.append(s)
    return out


# ----------------------------------------------------------------------------- energy preferences
def parse_energy_prefs(prefs: dict | None) -> dict[str, list[dict]]:
    """Flatten the energy dashboard preferences (old and new grid formats) into simple lists."""
    out: dict[str, list[dict]] = {k: [] for k in ("imp", "exp", "solar", "battery", "gas", "water", "devices")}
    if not prefs:
        return out
    for src in prefs.get("energy_sources", []):
        typ = src.get("type")
        if typ == "grid":
            # Old format: flow_from / flow_to lists. New format (2026+): one grid source per tariff.
            flows_from = src.get("flow_from") or ([src] if src.get("stat_energy_from") else [])
            flows_to = src.get("flow_to") or ([src] if src.get("stat_energy_to") else [])
            for f in flows_from:
                stat = f.get("stat_energy_from")
                if stat:
                    priced = f.get("entity_energy_price") or f.get("number_energy_price") is not None
                    out["imp"].append({"stat": stat, "cost": f.get("stat_cost") or (f"{stat}_cost" if priced else None)})
            for f in flows_to:
                stat = f.get("stat_energy_to")
                if stat:
                    priced = f.get("entity_energy_price_export") or f.get("number_energy_price_export") is not None
                    out["exp"].append({"stat": stat, "cost": f.get("stat_compensation") or (f"{stat}_compensation" if priced else None)})
        elif typ == "solar" and src.get("stat_energy_from"):
            out["solar"].append({"stat": src["stat_energy_from"], "name": src.get("name")})
        elif typ == "battery" and src.get("stat_energy_from"):
            out["battery"].append({"name": src.get("name"), "discharge": src["stat_energy_from"],
                                   "charge": src.get("stat_energy_to")})
        elif typ in ("gas", "water") and src.get("stat_energy_from"):
            stat = src["stat_energy_from"]
            priced = src.get("entity_energy_price") or src.get("number_energy_price") is not None
            out[typ].append({"stat": stat, "cost": src.get("stat_cost") or (f"{stat}_cost" if priced else None)})
    for dev in prefs.get("device_consumption", []):
        if dev.get("stat_consumption"):
            out["devices"].append({"stat": dev["stat_consumption"], "name": dev.get("name"),
                                   "parent": dev.get("included_in_stat")})
    return out


# ----------------------------------------------------------------------------- statistics helpers
def hourly_deltas(rows: list[dict], hours: list[int], cap: float | None) -> tuple[dict[int, float], list[int]]:
    """Per-hour increase of a cumulative ``sum`` series.

    A gap in the statistics is attributed to the first hour after the gap (the sum is cumulative).
    Steps above ``cap`` per hour are glitches: they count as 0 and their hour is returned in the second value
    so related series (costs) can skip the same hours. Negative steps (a meter that resets per session, or a
    correction) count as 0 without being reported.
    """
    t0, t1 = hours[0], hours[-1] + 3600
    out: dict[int, float] = {}
    glitches: list[int] = []
    prev = None
    for row in rows:
        ts, s = int(row["start"]), row.get("sum")
        if s is None:
            continue
        if prev is not None and ts - prev[0] >= 3600:
            gap_h = max(1, round((ts - prev[0]) / 3600))
            d = s - prev[1]
            if cap is not None and d > cap * gap_h:
                if t0 <= ts < t1:
                    glitches.append(ts)
                d = 0.0
            elif cap is not None and d < 0:
                d = 0.0
            if t0 <= ts < t1:
                out[ts] = d
        prev = (ts, s)
    return out, glitches


def first_start(rows: list[dict]) -> int | None:
    return int(rows[0]["start"]) if rows else None


def add_into(target: dict[int, float], src: dict[int, float]) -> None:
    for k, v in src.items():
        target[k] = target.get(k, 0.0) + v


def total(d: dict[int, float], hours: list[int]) -> float:
    return sum(d.get(h, 0.0) for h in hours)


async def first_month(src) -> tuple[int, int] | None:
    """The first calendar month with grid statistics (reports before that would be empty)."""
    prefs = parse_energy_prefs(await src.energy_prefs())
    ids = {x["stat"] for x in prefs["imp"]}
    if not ids:
        return None
    cfg = await src.config()
    tz = ZoneInfo(cfg["time_zone"])
    rows = await src.statistics(ids, dt.datetime(2000, 1, 1, tzinfo=tz), dt.datetime.now(tz), "month", {"energy": "kWh"}, {"sum"})
    starts = [r["start"] for v in rows.values() for r in v]
    if not starts:
        return None
    t = dt.datetime.fromtimestamp(min(starts), tz)
    return t.year, t.month


# ----------------------------------------------------------------------------- collector
class Collector:
    def __init__(self, source: Any, options: dict | None = None, cache: dict | None = None) -> None:
        self.src = source
        self.opt = options or {}
        self.cache = cache if cache is not None else {}

    async def collect(self, year: int, month: int) -> dict:
        cfg = await self.src.config()
        tz = ZoneInfo(cfg["time_zone"])
        start, end = month_bounds(year, month, tz)
        hours = hour_starts(start, end)
        metric = cfg.get("unit_system", "metric") != "us_customary"
        units = {
            "energy": "kWh",
            "currency": cfg.get("currency") or "EUR",
            "temperature": "°C" if metric else "°F",
            "water": "L" if metric else "gal",
            "gas": "m³" if metric else "ft³",
        }
        doc: dict[str, Any] = {
            "schema": SCHEMA_VERSION,
            "period": {"year": year, "month": month, "start": start.isoformat(), "end": end.isoformat(),
                       "hours": len(hours), "time_zone": cfg["time_zone"]},
            "generated": dt.datetime.now(tz).isoformat(timespec="minutes"),
            "units": units,
            "notes": [],
        }
        prefs = parse_energy_prefs(await self.src.energy_prefs())
        price = await self._energy(doc, prefs, start, end, hours, tz)
        await self._devices(doc, prefs, start, end, hours, price)
        await self._volume(doc, prefs, "water", start, end, hours, units["water"], cap=2000 if metric else 500)
        await self._volume(doc, prefs, "gas", start, end, hours, units["gas"], cap=25 if metric else 900)
        await self._weather(doc, cfg, start, end, hours, tz, metric)
        await self._indoor(doc, start, end, hours, metric)
        doc["sections"] = [k for k in ("energy", "devices", "batteries", "water", "gas", "weather", "indoor") if doc.get(k)]
        return doc

    # ------------------------------------------------------------------ fetch helpers
    async def _sums(self, ids: set[str], start, end, units: dict) -> dict[str, list[dict]]:
        ids = {i for i in ids if i}
        if not ids:
            return {}
        # Start a few hours early so the first hour of the month has a previous sum to subtract from.
        return await self.src.statistics(ids, start - dt.timedelta(hours=3), end, "hour", units, {"sum"})

    # ------------------------------------------------------------------ energy
    async def _energy(self, doc, prefs, start, end, hours, tz) -> dict[int, float]:
        cap = float(self.opt.get("max_hourly_kwh") or DEFAULT_MAX_HOURLY_KWH)
        energy_ids = {x["stat"] for k in ("imp", "exp", "solar") for x in prefs[k]}
        energy_ids |= {x[k] for x in prefs["battery"] for k in ("charge", "discharge") if x.get(k)}
        cost_ids = {x["cost"] for k in ("imp", "exp") for x in prefs[k] if x.get("cost")}
        if not prefs["imp"]:
            doc["notes"].append("no_grid")
            return {}
        rows = await self._sums(energy_ids | cost_ids, start, end, {"energy": "kWh"})
        glitched: dict[str, int] = {}

        def series(stat: str) -> tuple[dict[int, float], list[int]]:
            d, g = hourly_deltas(rows.get(stat, []), hours, cap)
            if g:
                glitched[stat] = len(g)
            return d, g

        def cost_series(stat: str | None, skip: list[int]) -> dict[int, float] | None:
            if not stat or stat not in rows or not rows[stat]:
                return None
            d, _ = hourly_deltas(rows[stat], hours, None)
            for h in skip:
                d.pop(h, None)
            return d

        imp: dict[int, float] = {}
        exp: dict[int, float] = {}
        solar: dict[int, float] = {}
        chg: dict[int, float] = {}
        dis: dict[int, float] = {}
        cost_imp: dict[int, float] = {}
        comp_exp: dict[int, float] = {}
        has_cost = has_comp = False
        partial_from = None
        for x in prefs["imp"]:
            d, g = series(x["stat"])
            add_into(imp, d)
            c = cost_series(x.get("cost"), g)
            if c is not None:
                has_cost = True
                add_into(cost_imp, c)
            fs = first_start(rows.get(x["stat"], []))
            if fs is None or fs > hours[0] + PARTIAL_GRACE_S:
                partial_from = fs
        for x in prefs["exp"]:
            d, g = series(x["stat"])
            add_into(exp, d)
            c = cost_series(x.get("cost"), g)
            if c is not None:
                has_comp = True
                add_into(comp_exp, c)
        for x in prefs["solar"]:
            add_into(solar, series(x["stat"])[0])
        batteries = []
        for x in prefs["battery"]:
            c = series(x["charge"])[0] if x.get("charge") else {}
            d = series(x["discharge"])[0]
            add_into(chg, c)
            add_into(dis, d)
            kc, kd = total(c, hours), total(d, hours)
            batteries.append({"name": x.get("name") or x["discharge"], "charge": kc, "discharge": kd,
                              "efficiency": kd / kc if kc > 0.5 else None})

        if not any(rows.get(x["stat"]) for x in prefs["imp"]):
            doc["notes"].append("no_grid_data")
            return {}

        load = {h: imp.get(h, 0) - exp.get(h, 0) + solar.get(h, 0) + dis.get(h, 0) - chg.get(h, 0) for h in hours}
        t_imp, t_exp, t_sol = total(imp, hours), total(exp, hours), total(solar, hours)
        t_chg, t_dis = total(chg, hours), total(dis, hours)
        t_load = sum(load.values())
        t_cost = total(cost_imp, hours) if has_cost else None
        t_comp = total(comp_exp, hours) if has_comp else None

        # Hourly grid price derived from the cost statistics; used to value device consumption.
        price: dict[int, float] = {}
        if has_cost:
            for h in hours:
                if imp.get(h, 0) > 0.05 and h in cost_imp:
                    price[h] = cost_imp[h] / imp[h]

        days: dict[str, dict[str, float]] = {}
        by_hour = [0.0] * 24
        n_by_hour = [0] * 24
        for h in hours:
            t = dt.datetime.fromtimestamp(h, tz)
            k = t.strftime("%Y-%m-%d")
            x = days.setdefault(k, {"d": k, "import": 0.0, "export": 0.0, "solar": 0.0, "load": 0.0, "cost": 0.0})
            x["import"] += imp.get(h, 0)
            x["export"] += exp.get(h, 0)
            x["solar"] += solar.get(h, 0)
            x["load"] += load[h]
            x["cost"] += cost_imp.get(h, 0) - comp_exp.get(h, 0)
            by_hour[t.hour] += load[h]
            n_by_hour[t.hour] += 1

        positive = sorted(v for v in load.values() if v > 0)
        base_w = positive[int(len(positive) * 0.05)] * 1000 if len(positive) > 48 else None
        peak_h = max(hours, key=lambda h: load[h]) if hours else None
        fixed = self._fixed_costs(len(days))

        doc["energy"] = {
            "import": t_imp, "export": t_exp, "solar": t_sol, "battery_charge": t_chg, "battery_discharge": t_dis,
            "consumption": t_load,
            "self_consumed_solar": max(0.0, t_sol - t_exp) if t_sol else None,
            "self_sufficiency": (1 - t_imp / t_load) if t_load > 0 and (t_sol or t_dis) else None,
            "cost_import": t_cost, "compensation": t_comp,
            "net_cost": (t_cost or 0) - (t_comp or 0) if has_cost else None,
            "avg_import_price": (t_cost / t_imp) if has_cost and t_imp > 0 else None,
            "fixed_costs": fixed,
            "total_cost": ((t_cost or 0) - (t_comp or 0) + (fixed or 0)) if has_cost else None,
            "base_load_w": base_w,
            "peak": {"kw": load[peak_h], "at": dt.datetime.fromtimestamp(peak_h, tz).isoformat(timespec="minutes")} if peak_h else None,
            "by_hour_w": [by_hour[i] / n_by_hour[i] * 1000 if n_by_hour[i] else None for i in range(24)],
            "daily": [days[k] for k in sorted(days)],
            "partial_from": dt.datetime.fromtimestamp(partial_from, tz).date().isoformat() if partial_from else None,
            "glitch_hours": glitched,
        }
        if batteries:
            doc["batteries"] = {"units": batteries, "charge": t_chg, "discharge": t_dis,
                                "efficiency": t_dis / t_chg if t_chg > 0.5 else None}
        doc["_load"] = load  # internal, removed before saving
        return price

    def _fixed_costs(self, days: int) -> float | None:
        daily = self.opt.get("fixed_costs_daily")
        monthly = self.opt.get("fixed_costs_monthly")
        if not daily and not monthly:
            return None
        return float(daily or 0) * days + float(monthly or 0)

    # ------------------------------------------------------------------ devices
    async def _devices(self, doc, prefs, start, end, hours, price) -> None:
        if not prefs["devices"] or "energy" not in doc:
            doc.pop("_load", None)
            return
        cap = float(self.opt.get("max_hourly_kwh") or DEFAULT_MAX_HOURLY_KWH)
        rows = await self._sums({d["stat"] for d in prefs["devices"]}, start, end, {"energy": "kWh"})
        avg_price = doc["energy"].get("avg_import_price")
        load_total = doc["energy"]["consumption"]
        out = []
        for d in prefs["devices"]:
            r = rows.get(d["stat"], [])
            series, g = hourly_deltas(r, hours, cap)
            kwh = total(series, hours)
            value = None
            if avg_price is not None:
                value = sum(v * price.get(h, avg_price) for h, v in series.items())
            fs = first_start(r)
            out.append({"name": d.get("name") or d["stat"], "stat": d["stat"], "parent": d.get("parent"),
                        "kwh": kwh, "value": value, "share": kwh / load_total if load_total > 0 else None,
                        "partial": fs is None or fs > hours[0] + PARTIAL_GRACE_S, "glitch_hours": len(g),
                        "no_data": kwh < 0.01})
        top = sum(x["kwh"] for x in out if not x["parent"])
        out.sort(key=lambda x: -x["kwh"])
        doc["devices"] = {"items": out, "tracked": top, "untracked": max(0.0, load_total - top),
                          "untracked_share": max(0.0, load_total - top) / load_total if load_total > 0 else None}
        doc.pop("_load", None)

    # ------------------------------------------------------------------ water / gas
    async def _volume(self, doc, prefs, kind, start, end, hours, unit, cap) -> None:
        items = prefs[kind]
        if not items:
            return
        ids = {x["stat"] for x in items} | {x["cost"] for x in items if x.get("cost")}
        rows = await self._sums(ids, start, end, {"volume": unit, "energy": "kWh"})
        amount = 0.0
        cost = None
        days: dict[int, float] = {}
        for x in items:
            d, g = hourly_deltas(rows.get(x["stat"], []), hours, cap)
            amount += total(d, hours)
            add_into(days, d)
            if x.get("cost") and rows.get(x["cost"]):
                c, _ = hourly_deltas(rows[x["cost"]], hours, None)
                for h in g:
                    c.pop(h, None)
                cost = (cost or 0) + total(c, hours)
        if not any(rows.get(x["stat"]) for x in items):
            return
        meta = await self.src.statistics_meta({x["stat"] for x in items})
        stat_unit = next((m.get("unit") for m in meta.values() if m), None)
        # Gas can be metered in energy units; keep the unit that was actually used.
        if kind == "gas" and stat_unit and meta and next(iter(meta.values())).get("unit_class") == "energy":
            unit = "kWh"
        doc[kind] = {"amount": amount, "unit": unit, "cost": cost, "per_day": amount / max(1, len(hours) / 24)}

    # ------------------------------------------------------------------ weather
    async def _weather(self, doc, cfg, start, end, hours, tz, metric) -> None:
        lat, lon = cfg.get("latitude"), cfg.get("longitude")
        if lat is None or lon is None:
            return
        try:
            daily = await weather.daily(self.src, lat, lon, start.date(), (end - dt.timedelta(days=1)).date(), cfg["time_zone"])
            normals = await weather.normals(self.src, lat, lon, self.cache)
        except Exception as err:  # network problems must not break the report
            _LOGGER.warning("Open-Meteo request failed: %s", err)
            doc["notes"].append("weather_unavailable")
            return
        # Optional local outdoor sensor overrides the modelled temperature.
        sensor = self.opt.get("outdoor_sensor")
        if sensor:
            st = await self.src.statistics({sensor}, start, end, "hour", {"temperature": "°C"}, {"mean", "min", "max"})
            rows = st.get(sensor, [])
            if len(rows) >= MIN_COVERAGE * len(hours):
                per: dict[str, dict] = {}
                for r in rows:
                    k = dt.datetime.fromtimestamp(r["start"], tz).strftime("%Y-%m-%d")
                    x = per.setdefault(k, {"m": [], "lo": [], "hi": []})
                    for key, col in (("m", "mean"), ("lo", "min"), ("hi", "max")):
                        if r.get(col) is not None:
                            x[key].append(r[col])
                for day in daily:
                    x = per.get(day["d"])
                    if x and x["m"]:
                        day["mean"], day["min"], day["max"] = sum(x["m"]) / len(x["m"]), min(x["lo"]), max(x["hi"])
                doc["notes"].append("outdoor_sensor")
        doc["weather"] = weather.summarize(daily, normals, start.month, metric)
        doc["weather"]["source"] = "sensor" if "outdoor_sensor" in doc["notes"] else "open-meteo"

    # ------------------------------------------------------------------ indoor climate
    async def _indoor(self, doc, start, end, hours, metric) -> None:
        sensors = await self.src.climate_sensors()
        outdoor = self.opt.get("outdoor_sensor")
        if self.opt.get("excluded_areas") is not None:
            excluded = set(self.opt["excluded_areas"])
        else:  # not configured yet: skip areas whose name suggests they are outside
            excluded = {s["area_id"] for s in sensors
                        if is_outdoor_name(s.get("area_name") or "") or is_outdoor_name(s.get("floor_name") or "")}
        sensors = [s for s in sensors if s.get("area_id") and s["area_id"] not in excluded and s["entity_id"] != outdoor]
        if not sensors:
            return
        st = await self.src.statistics({s["entity_id"] for s in sensors}, start, end, "hour",
                                       {"temperature": "°C"}, {"mean", "min", "max"})
        plausible = {"temperature": (5.0, 35.0), "humidity": (10.0, 100.0), "carbon_dioxide": (250.0, 5000.0)}
        usable = []
        for s in sensors:
            rows = [r for r in st.get(s["entity_id"], []) if r.get("mean") is not None]
            if len(rows) < MIN_COVERAGE * len(hours):
                continue
            m = sum(r["mean"] for r in rows) / len(rows)
            lo, hi = plausible[s["device_class"]]
            if lo <= m <= hi:  # drops e.g. heat-pump water temperatures or a freezer in a utility room
                usable.append({**s, "_rows": rows, "_mean": m})
        areas: dict[str, dict] = {}
        for s in prefer_room_sensors(usable):
            rows, m = s["_rows"], s["_mean"]
            a = areas.setdefault(s["area_id"], {"area_id": s["area_id"], "name": s.get("area_name") or s["area_id"],
                                                "floor": s.get("floor_name"), "_v": {}})
            v = a["_v"].setdefault(s["device_class"], {"means": [], "hourly": {}, "min": [], "max": [], "n": 0})
            v["means"].append(m)
            v["n"] += 1
            for r in rows:
                v["hourly"].setdefault(int(r["start"]), []).append(r["mean"])
                if r.get("min") is not None:
                    v["min"].append(r["min"])
                if r.get("max") is not None:
                    v["max"].append(r["max"])
        out = []
        for a in areas.values():
            item = {k: a[k] for k in ("area_id", "name", "floor")}
            for dc, v in a.pop("_v").items():
                key = {"temperature": "temp", "humidity": "humidity", "carbon_dioxide": "co2"}[dc]
                # Median per hour across the area's sensors, then month statistics of that series.
                series = [pystats.median(x) for x in v["hourly"].values()]
                item[key] = sum(series) / len(series)
                item[key + "_sensors"] = v["n"]
                if dc == "temperature":
                    item["temp_min"], item["temp_max"] = min(v["min"] or series), max(v["max"] or series)
                if dc == "humidity":
                    item["humid_hours"] = sum(1 for x in series if x > 70)
                if dc == "carbon_dioxide":
                    item["co2_over_1000"] = sum(1 for x in series if x > 1000) / len(series)
            out.append(item)
        if not out:
            return
        temps = [a["temp"] for a in out if "temp" in a]
        hums = [a["humidity"] for a in out if "humidity" in a]
        co2 = [a["co2"] for a in out if "co2" in a]
        conv = (lambda c: c) if metric else (lambda c: c * 9 / 5 + 32)
        for a in out:
            for k in ("temp", "temp_min", "temp_max"):
                if k in a:
                    a[k] = conv(a[k])
        out.sort(key=lambda a: (a.get("floor") or "", a["name"]))
        doc["indoor"] = {
            "temp": conv(pystats.median(temps)) if temps else None,
            "humidity": pystats.median(hums) if hums else None,
            "co2": pystats.median(co2) if co2 else None,
            "warmest": max((a for a in out if "temp" in a), key=lambda a: a["temp"], default=None),
            "coolest": min((a for a in out if "temp" in a), key=lambda a: a["temp"], default=None),
            "areas": out,
        }
        if doc["indoor"]["warmest"]:
            doc["indoor"]["warmest"] = doc["indoor"]["warmest"]["name"]
            doc["indoor"]["coolest"] = doc["indoor"]["coolest"]["name"]
