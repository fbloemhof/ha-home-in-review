"""Optional report sections: heat pump, TeslaMate and custom tiles. Each is skipped when not configured."""
from __future__ import annotations

import datetime as dt
import logging
import re
from typing import Any

_LOGGER = logging.getLogger(__name__)

HOME_WORDS = re.compile(r"^(home|thuis|thús|zuhause|maison|casa|hjem|hemma|koti)$", re.I)


# ============================================================================ heat pump
def as_list(v) -> list[str]:
    if not v:
        return []
    return [v] if isinstance(v, str) else list(v)


async def heat_pump(col, doc: dict, start, end, hours, cap: float) -> None:
    """Any brand: electricity from one or more energy sensors (energy-dashboard devices, a kWh meter, a smart plug
    or the heat pump's own integration) and, optionally, heat delivered from one or more energy sensors (many
    brands report heating and hot water separately). Gives COP and kWh per degree day."""
    from .collector import (  # local import: collector imports this module
        hourly_deltas,
        total,
    )

    elec_ids = as_list(col.opt.get("heat_pump_devices"))
    heat_ids = as_list(col.opt.get("heat_pump_heat_sensor"))
    if not elec_ids:
        return
    rows = await col._sums(set(elec_ids) | set(heat_ids), start, end, {"energy": "kWh"})
    elec = sum(total(hourly_deltas(rows.get(d, []), hours, cap)[0], hours) for d in elec_ids)
    heat = None
    if any(rows.get(h) for h in heat_ids):
        # Heat output can be several times the electrical input; allow a COP of up to 8 per hour.
        heat = sum(total(hourly_deltas(rows.get(h, []), hours, cap * 8)[0], hours) for h in heat_ids)
    if elec < 0.01 and not heat:
        return
    hp: dict[str, Any] = {"electricity": elec, "heat": heat, "cop": heat / elec if heat and elec > 0.5 else None,
                          "degree_days": (doc.get("weather") or {}).get("degree_days")}
    if hp["degree_days"]:
        hp["kwh_per_degree_day"] = elec / hp["degree_days"]
    e = doc.get("energy") or {}
    if e.get("consumption"):
        hp["share"] = elec / e["consumption"]
    names = {x["stat"]: x["name"] for x in (doc.get("devices") or {}).get("items", [])}
    missing = [d for d in elec_ids if d not in names]
    if missing:
        names.update(await col.src.names(set(missing)))
    hp["devices"] = [names.get(d, d) for d in elec_ids]
    doc["heat_pump"] = hp


# ============================================================================ any car (odometer + charger)
async def car_generic(col, doc: dict, start, end, hours, cap: float) -> None:
    """Any brand: kilometres from odometer sensors (one per car) and home charging from charger energy sensors.

    km per car = highest odometer reading this month minus the highest reading before the month (or the lowest in
    the month for the first month). kWh per 100 km is an estimate: it only knows the energy charged at home.
    """
    from .collector import hourly_deltas, total

    odos = as_list(col.opt.get("car_odometers"))
    chargers = as_list(col.opt.get("car_chargers"))
    if not odos and not chargers:
        return
    cars = []
    if odos:
        # Unit conversion to km; odometers in miles come back as km and are shown in the user's unit later.
        # Odometers are usually total_increasing (statistics keep "state"); some are measurements ("max"/"mean").
        st = await col.src.statistics(set(odos), start - dt.timedelta(days=3), end, "hour", {"distance": "km"},
                                      {"max", "mean", "state"})
        names = await col.src.device_names(set(odos))
        for o in odos:
            def val(r: dict) -> float | None:
                return next((r[k] for k in ("state", "max", "mean") if r.get(k) is not None), None)

            rows = [r for r in st.get(o, []) if val(r) is not None]
            before = [val(r) for r in rows if r["start"] < start.timestamp()]
            inside = [val(r) for r in rows if r["start"] >= start.timestamp()]
            if not inside:
                continue
            base = max(before) if before else min(inside)
            km = max(0.0, max(inside) - base)
            cars.append({"name": names.get(o, o), "km": km, "drives": None, "longest_km": None, "charged": None,
                         "charged_home": None, "wh_per_km": None, "odometer_end": max(inside)})
    home_kwh = None
    if chargers:
        rows = await col._sums(set(chargers), start, end, {"energy": "kWh"})
        if any(rows.get(c) for c in chargers):
            home_kwh = sum(total(hourly_deltas(rows.get(c, []), hours, cap)[0], hours) for c in chargers)
    if not cars and home_kwh is None:
        return
    km = sum(c["km"] for c in cars)
    doc["car"] = {"cars": cars, "km": km, "drives": None, "charged": home_kwh, "charged_home": home_kwh,
                  "kwh_per_100km_home": (home_kwh / km * 100) if home_kwh and km > 10 else None, "source": "sensors"}


# ============================================================================ TeslaMate
class TeslaMate:
    """Read-only access to TeslaMate through Grafana's query API (a Viewer service-account token is enough)."""

    def __init__(self, src, url: str, token: str) -> None:
        self.src = src
        self.url = url.rstrip("/")
        self.headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        self.uid: str | None = None

    async def _datasource(self) -> str:
        if self.uid:
            return self.uid
        sources = await self.src.request_json("GET", f"{self.url}/api/datasources", headers=self.headers)
        pg = [x for x in sources if "postgres" in (x.get("type") or "")]
        pick = next((x for x in pg if (x.get("name") or "").lower() == "teslamate"), pg[0] if pg else None)
        if not pick:
            raise RuntimeError("no PostgreSQL data source found in Grafana")
        self.uid = pick["uid"]
        return self.uid

    async def query(self, sql: str) -> list[dict]:
        body = {"queries": [{"refId": "A", "datasource": {"uid": await self._datasource()}, "format": "table",
                             "rawSql": sql}], "from": "now-1h", "to": "now"}
        res = await self.src.request_json("POST", f"{self.url}/api/ds/query", headers=self.headers, json=body)
        res = res["results"]["A"]
        if res.get("error"):
            raise RuntimeError(res["error"])
        f = res["frames"][0]
        names = [x["name"] for x in f["schema"]["fields"]]
        values = f["data"]["values"]
        return [dict(zip(names, row, strict=False)) for row in zip(*values, strict=False)] if values else []


async def teslamate(col, doc: dict, start: dt.datetime, end: dt.datetime) -> None:
    url, token = col.opt.get("teslamate_grafana_url"), col.opt.get("teslamate_grafana_token")
    if not url or not token:
        return
    tm = TeslaMate(col.src, url, token)
    lo = start.astimezone(dt.UTC).strftime("%Y-%m-%d %H:%M:%S")
    hi = end.astimezone(dt.UTC).strftime("%Y-%m-%d %H:%M:%S")
    home = (col.opt.get("teslamate_home_geofence") or "").strip().lower()
    try:
        cars = await tm.query(f"""select c.id, coalesce(c.name, c.model, 'Car') as name,
            count(d.id) as drives, coalesce(sum(d.distance), 0) as km, coalesce(max(d.distance), 0) as longest,
            coalesce(sum(d.duration_min), 0) as minutes
            from cars c left join drives d on d.car_id = c.id and d.start_date >= '{lo}' and d.start_date < '{hi}'
            group by c.id order by c.id""")
        charging = await tm.query(f"""select c.car_id, coalesce(g.name, '') as place, count(*) as sessions,
            coalesce(sum(c.charge_energy_added), 0) as added, coalesce(sum(c.charge_energy_used), 0) as used
            from charging_processes c left join geofences g on g.id = c.geofence_id
            where c.start_date >= '{lo}' and c.start_date < '{hi}' group by 1, 2""")
        eff = await tm.query(f"""select d.car_id,
            sum((d.start_rated_range_km - d.end_rated_range_km) * c.efficiency) as kwh, sum(d.distance) as km
            from drives d join cars c on c.id = d.car_id
            where d.start_date >= '{lo}' and d.start_date < '{hi}' and d.distance > 1 group by 1""")
    except Exception as err:  # unreachable Grafana must not break the report
        _LOGGER.warning("TeslaMate query failed: %s", err)
        doc["notes"].append("teslamate_unavailable")
        return
    out = []
    for c in cars:
        ch = [x for x in charging if x["car_id"] == c["id"]]
        if home:
            at_home = [x for x in ch if (x["place"] or "").lower() == home]
        else:
            at_home = [x for x in ch if HOME_WORDS.match(x["place"] or "")]
        e = next((x for x in eff if x["car_id"] == c["id"]), None)
        out.append({
            "name": c["name"], "drives": int(c["drives"] or 0), "km": float(c["km"] or 0), "longest_km": float(c["longest"] or 0),
            "hours": float(c["minutes"] or 0) / 60,
            "charged": sum(float(x["added"] or 0) for x in ch),
            "charged_home": sum(float(x["added"] or 0) for x in at_home),
            "sessions": sum(int(x["sessions"] or 0) for x in ch),
            "wh_per_km": (float(e["kwh"]) * 1000 / float(e["km"])) if e and e["km"] and e["kwh"] else None,
        })
    out = [x for x in out if x["km"] > 0 or x["charged"] > 0]
    if out:
        doc["car"] = {"cars": out, "km": sum(x["km"] for x in out), "drives": sum(x["drives"] for x in out),
                      "charged": sum(x["charged"] for x in out), "source": "teslamate"}


# ============================================================================ custom tiles
TILE_TYPES = ("sum", "mean", "max", "min", "hours_above")


async def custom_tiles(col, doc: dict, start, end, hours) -> None:
    """User-defined figures from any statistic: total increase, average, extremes or hours above a threshold."""
    from .collector import hourly_deltas, total

    tiles = col.opt.get("custom_tiles") or []
    if not tiles:
        return
    ids = {t["statistic"] for t in tiles if t.get("statistic")}
    sums = await col._sums({t["statistic"] for t in tiles if t.get("type") == "sum"}, start, end, {})
    means = await col.src.statistics({i for i in ids if any(t["statistic"] == i and t.get("type") != "sum" for t in tiles)},
                                     start, end, "hour", {}, {"mean", "min", "max"}) if ids else {}
    out = []
    for t in tiles:
        sid, typ = t.get("statistic"), t.get("type", "sum")
        value = None
        if typ == "sum" and sums.get(sid):
            value = total(hourly_deltas(sums[sid], hours, None)[0], hours)
        else:
            rows = means.get(sid) or []
            vals = [r[c] for r in rows for c in ([{"mean": "mean", "hours_above": "mean"}.get(typ, typ)]) if r.get(c) is not None]
            if vals:
                if typ == "mean":
                    value = sum(vals) / len(vals)
                elif typ == "max":
                    value = max(vals)
                elif typ == "min":
                    value = min(vals)
                elif typ == "hours_above":
                    value = float(sum(1 for v in vals if v > float(t.get("threshold") or 0)))
        out.append({"name": t.get("name") or sid, "statistic": sid, "type": typ, "value": value,
                    "unit": "h" if typ == "hours_above" else (t.get("unit") or ""), "decimals": int(t.get("decimals", 0))})
    if any(x["value"] is not None for x in out):
        doc["custom"] = out
