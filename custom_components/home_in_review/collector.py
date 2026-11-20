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
import re
import statistics as pystats
from typing import Any
from zoneinfo import ZoneInfo

from . import extras, gas, weather
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
    words = re.findall(r"[^\W\d_]+", name.lower())
    return any(w == h or w.endswith(h) for w in words for h in OUTDOOR_AREA_HINTS)


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
                s["_drop"] = "co2_module"
                continue
            if s["area_id"] in climate_areas and s.get("device_id") not in humid_devices:
                s["_drop"] = "not_room_sensor"
                continue
        out.append(s)
    return out


# ----------------------------------------------------------------------------- energy preferences
SECTIONS = ("energy", "devices", "batteries", "heat_pump", "car", "water", "gas", "weather", "indoor", "custom")
# Notes of outside services that were unreachable: the report is incomplete for a reason that may pass.
UNAVAILABLE = {"teslamate_unavailable": "car", "evcc_unavailable": "car"}


def sections(doc: dict) -> list[str]:
    return [k for k in SECTIONS if doc.get(k)]


def power_rate(src: dict) -> dict | None:
    """The power sensor(s) of an energy source (energy dashboard, 2025.12+): one signed sensor (``stat_rate``,
    positive = discharging / importing / producing, optionally inverted) or one sensor per direction."""
    pc = src.get("power_config") or {}
    if pc.get("stat_rate_from") or pc.get("stat_rate_to"):
        return {"from": pc.get("stat_rate_from"), "to": pc.get("stat_rate_to")}
    stat = pc.get("stat_rate") or src.get("stat_rate")
    return {"stat": stat, "inverted": bool(pc.get("stat_rate_inverted"))} if stat else None


def parse_energy_prefs(prefs: dict | None) -> dict[str, list[dict]]:
    """Flatten the energy dashboard preferences (old and new grid formats) into simple lists."""
    out: dict[str, list[dict]] = {k: [] for k in ("imp", "exp", "solar", "battery", "gas", "water", "devices",
                                                  "grid_rate")}
    if not prefs:
        return out
    for src in prefs.get("energy_sources", []):
        typ = src.get("type")
        if typ == "grid":
            if rate := power_rate(src):
                out["grid_rate"].append(rate)
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
            out["solar"].append({"stat": src["stat_energy_from"], "name": src.get("name"), "rate": power_rate(src)})
        elif typ == "battery" and src.get("stat_energy_from"):
            out["battery"].append({"name": src.get("name"), "discharge": src["stat_energy_from"],
                                   "charge": src.get("stat_energy_to"), "rate": power_rate(src),
                                   "soc": src.get("stat_soc")})
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
        self.price: dict[int, float] = {}
        self.avg_price: float | None = None
        self.mean_price: float | None = None
        self.battery_hours: list[tuple[dict[int, float], dict[int, float]]] = []
        self.gas_hours: dict[int, float] = {}
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
        # Hourly price (what a kWh cost in that hour) for valuing the heat pump and home charging.
        self.price = price
        self.avg_price = (doc.get("energy") or {}).get("avg_import_price")
        # Plain average of the hourly prices: the reference for "smart" use (charging when it is cheap).
        self.mean_price = (sum(price.values()) / len(price)) if price else None
        await extras.power(self, doc, prefs, start, end, hours, tz)
        await self._devices(doc, prefs, start, end, hours, price)
        await self._volume(doc, prefs, "water", start, end, hours, units["water"], cap=2000 if metric else 500)
        await self._volume(doc, prefs, "gas", start, end, hours, units["gas"], cap=25 if metric else 900)
        await self._weather(doc, cfg, start, end, hours, tz, metric)
        await self._indoor(doc, start, end, hours, metric)
        self._gas_heating(doc, metric)
        await self._gas_boiler(doc, start, end, hours)
        self._totals(doc)
        cap = float(self.opt.get("max_hourly_kwh") or DEFAULT_MAX_HOURLY_KWH)
        await extras.heat_pump(self, doc, start, end, hours, cap)
        # Car sources, richest first: TeslaMate, evcc, then odometer + charger sensors.
        await extras.teslamate(self, doc, start, end)
        if "car" not in doc:
            await extras.evcc(self, doc, start, end)
            if "car" in doc and self.opt.get("car_odometers") and not any(c["km_known"] for c in doc["car"]["cars"]):
                # evcc rarely knows the odometer; take kilometres from the odometer sensors when configured.
                sensors: dict = {"notes": [], "period": doc["period"]}
                await extras.car_generic(self, sensors, start, end, hours, cap)
                if sensors.get("car"):
                    doc["car"]["km"] = sensors["car"]["km"]
                    doc["car"]["odometer_cars"] = sensors["car"]["cars"]
                    if doc["car"].get("cost") is not None and doc["car"]["km"] > 10:
                        doc["car"]["cost_per_100km"] = doc["car"]["cost"] / doc["car"]["km"] * 100
        if "car" not in doc:
            await extras.car_generic(self, doc, start, end, hours, cap)
        await extras.custom_tiles(self, doc, start, end, hours)
        doc["sections"] = sections(doc)
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
        self.battery_hours = []  # per battery: (charge per hour, discharge per hour), for valuing in extras.power
        for x in prefs["battery"]:
            c = series(x["charge"])[0] if x.get("charge") else {}
            d = series(x["discharge"])[0]
            add_into(chg, c)
            add_into(dis, d)
            self.battery_hours.append((c, d))
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

        # What a kWh used in each hour really cost, derived from the cost statistics; used to value devices.
        # In an hour where the house returned more than it took from the grid, extra use costs the export
        # compensation that was missed (when known); otherwise it costs the import price of that hour.
        price: dict[int, float] = {}
        if has_cost:
            for h in hours:
                i, x = imp.get(h, 0), exp.get(h, 0)
                if x > i and x > 0.05 and has_comp and h in comp_exp:
                    price[h] = comp_exp[h] / x
                elif i > 0.05 and h in cost_imp:
                    price[h] = cost_imp[h] / i

        days: dict[str, dict[str, float]] = {}
        by_hour = [0.0] * 24
        n_by_hour = [0] * 24
        for h in hours:
            t = dt.datetime.fromtimestamp(h, tz)
            k = t.strftime("%Y-%m-%d")
            x = days.setdefault(k, {"d": k, "import": 0.0, "export": 0.0, "solar": 0.0, "load": 0.0, "cost": 0.0,
                                    "bat_out": 0.0, "bat_in": 0.0})
            x["bat_out"] += dis.get(h, 0)
            x["bat_in"] += chg.get(h, 0)
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

    def _gas_heating(self, doc: dict, metric: bool) -> None:
        """Gas per degree day, and (when possible) heating versus hot water and cooking; see gas.py."""
        g, w = doc.get("gas"), doc.get("weather")
        if not g or not w or not w.get("daily"):
            return
        # Degree days exactly as on the weather slide (same threshold, weighting and unit).
        base, weighted = weather.dd_settings(metric, self.opt.get("degree_day_base"), self.opt.get("degree_days_weighted"))
        dd = {x["d"]: weather.degree_days(x["mean"], int(x["d"][5:7]), base, weighted)
              for x in w["daily"] if x.get("mean") is not None}
        daily = {x["d"]: x["v"] for x in g.get("daily", [])}
        keys = sorted(set(daily) | set(dd))
        res = gas.split([daily.get(k) for k in keys], [dd.get(k) for k in keys], self.opt.get("gas_base_per_day"),
                        hot_water_only=self.opt.get("gas_use") == "hot_water_only", unit=g.get("unit", "m³"),
                        fahrenheit=not metric)
        if res:
            g.update(res)

    async def _gas_boiler(self, doc: dict, start, end, hours) -> None:
        """Replace the estimated gas split by a measured one when the boiler's hot-water/heating on-time sensors
        (sensor.py) cover the whole month; otherwise the estimate stays."""
        g, boiler = doc.get("gas"), self.opt.get("_boiler") or {}
        if self.opt.get("gas_use") == "hot_water_only":
            return  # set by the user: all gas is hot water and cooking
        if not g or not boiler or not getattr(self, "gas_hours", None):
            return
        rows = await self._sums(set(boiler.values()), start, end, {"duration": "h"})
        series: dict[str, dict[int, float] | None] = {"dhw": None, "ch": None}
        for short, sid in boiler.items():
            fs = first_start(rows.get(sid, []))
            if fs is None or fs > hours[0] + PARTIAL_GRACE_S:
                return  # not recorded for the whole month yet
            series[short] = hourly_deltas(rows[sid], hours, 1.05)[0]
        res = gas.split_measured(self.gas_hours, series["dhw"], series["ch"], g.get("degree_days"))
        if res:
            g.update(res)

    @staticmethod
    def _totals(doc: dict) -> None:
        """Total energy cost = electricity (bought - sold) + gas + fixed costs. Water is shown separately."""
        e = doc.get("energy")
        gas = (doc.get("gas") or {}).get("cost")
        if not e:
            return
        parts = [e.get("net_cost"), gas]
        if all(p is None for p in parts):
            e["total_cost"] = None
            return
        e["gas_cost"] = gas
        e["total_cost"] = sum(p for p in parts if p is not None) + (e.get("fixed_costs") or 0)
        # Water is not energy, but belongs on the household bill: kept apart so either total can be shown.
        water = (doc.get("water") or {}).get("cost")
        e["water_cost"] = water
        e["bill_total"] = e["total_cost"] + (water or 0)

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
        tz = ZoneInfo(doc["period"]["time_zone"])
        per_day: dict[str, float] = {}
        for h, v in days.items():
            k = dt.datetime.fromtimestamp(h, tz).strftime("%Y-%m-%d")
            per_day[k] = per_day.get(k, 0.0) + v
        if kind == "gas":
            self.gas_hours = days  # gas per hour, for the split from the boiler's own status
        doc[kind] = {"amount": amount, "unit": unit, "cost": cost, "per_day": amount / max(1, len(hours) / 24),
                     "daily": [{"d": k, "v": per_day[k]} for k in sorted(per_day)]}

    # ------------------------------------------------------------------ weather
    async def _weather(self, doc, cfg, start, end, hours, tz, metric) -> None:
        """Daily weather: Open-Meteo (default) and/or the user's own outdoor temperature sensor."""
        use_om = self.opt.get("use_open_meteo", True)
        lat, lon = cfg.get("latitude"), cfg.get("longitude")
        days = [(start + dt.timedelta(days=i)).date() for i in range((end.date() - start.date()).days)]
        daily = [{"d": d.isoformat(), "mean": None, "min": None, "max": None, "precip": None, "sun_h": None} for d in days]
        normals = None
        if use_om and lat is not None and lon is not None:
            try:
                daily = await weather.daily(self.src, lat, lon, days[0], days[-1], cfg["time_zone"])
                normals = await weather.normals(self.src, lat, lon, self.cache)
            except Exception as err:  # network problems must not break the report
                _LOGGER.warning("Open-Meteo request failed: %s", err)
                doc["notes"].append("weather_unavailable")
        # Optional local outdoor sensor overrides the temperature.
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
                        day["mean"], day["min"], day["max"] = sum(x["m"]) / len(x["m"]), min(x["lo"] or x["m"]), max(x["hi"] or x["m"])
                doc["notes"].append("outdoor_sensor")
        # Optional rain gauge (a total_increasing precipitation sensor) replaces the modelled precipitation.
        rain = self.opt.get("rain_sensor")
        if rain:
            rows = (await self._sums({rain}, start, end, {"distance": "mm"})).get(rain, [])
            if rows and rows[0]["start"] <= start.timestamp() + PARTIAL_GRACE_S:
                per_hour, _ = hourly_deltas(rows, hours, 150.0)  # more than 150 mm in an hour is a glitch
                per_day: dict[str, float] = {}
                for h, v in per_hour.items():
                    k = dt.datetime.fromtimestamp(h, tz).strftime("%Y-%m-%d")
                    per_day[k] = per_day.get(k, 0.0) + v
                for day in daily:
                    day["precip"] = per_day.get(day["d"], 0.0)
                doc["notes"].append("rain_sensor")
        summary = weather.summarize(daily, normals, start.month, metric, self.opt.get("degree_day_base"),
                                    bool(self.opt.get("degree_days_weighted")))
        if summary:
            summary["source"] = ("sensor" if "outdoor_sensor" in doc["notes"] else "open-meteo") + ("" if use_om else "-only")
            # Where the weather is for, so a reader can check it: the coarse Open-Meteo location and/or the sensor.
            if use_om and lat is not None and lon is not None:
                summary["location"] = {"lat": weather.coarse(lat), "lon": weather.coarse(lon)}
            if "outdoor_sensor" in doc["notes"] and sensor:
                summary["sensor_name"] = (await self.src.names({sensor})).get(sensor, sensor)
            summary["rain_source"] = "sensor" if "rain_sensor" in doc["notes"] else ("open-meteo" if use_om else None)
            doc["weather"] = summary

    # ------------------------------------------------------------------ indoor climate
    async def _indoor(self, doc, start, end, hours, metric) -> None:
        sensors = await self.src.climate_sensors()
        outdoor = self.opt.get("outdoor_sensor")
        auto = self.opt.get("excluded_areas") is None
        if not auto:
            excluded = set(self.opt["excluded_areas"])
        else:  # not configured yet: skip areas whose name (or floor name) says they are outside
            excluded = {a["area_id"] for a in await self.src.areas()
                        if is_outdoor_name(a.get("name") or "") or is_outdoor_name(a.get("floor_name") or "")}
        names = {a["area_id"]: a["name"] for a in await self.src.areas()}
        # What was left out and why, so the report can say so.
        report = {"excluded_areas": sorted(names.get(a, a) for a in excluded), "excluded_auto": auto,
                  "no_area": sum(1 for s in sensors if not s.get("area_id")), "dropped": []}
        sensors = [s for s in sensors if s.get("area_id") and s["area_id"] not in excluded and s["entity_id"] != outdoor]
        if not sensors:
            doc["indoor_sources"] = report
            return
        st = await self.src.statistics({s["entity_id"] for s in sensors}, start, end, "hour",
                                       {"temperature": "°C"}, {"mean", "min", "max"})
        plausible = {"temperature": (5.0, 35.0), "humidity": (10.0, 100.0), "carbon_dioxide": (250.0, 5000.0)}
        usable = []
        for s in sensors:
            rows = [r for r in st.get(s["entity_id"], []) if r.get("mean") is not None]
            if len(rows) < MIN_COVERAGE * len(hours):
                report["dropped"].append({"name": s.get("name") or s["entity_id"], "area": s.get("area_name"), "reason": "coverage"})
                continue
            m = sum(r["mean"] for r in rows) / len(rows)
            lo, hi = plausible[s["device_class"]]
            if lo <= m <= hi:  # drops e.g. heat-pump water temperatures or a freezer in a utility room
                usable.append({**s, "_rows": rows, "_mean": m})
            else:
                report["dropped"].append({"name": s.get("name") or s["entity_id"], "area": s.get("area_name"), "reason": "implausible"})
        kept = prefer_room_sensors(usable)
        report["dropped"] += [{"name": s.get("name") or s["entity_id"], "area": s.get("area_name"), "reason": s["_drop"]}
                              for s in usable if s.get("_drop")]
        doc["indoor_sources"] = report
        areas: dict[str, dict] = {}
        for s in kept:
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
