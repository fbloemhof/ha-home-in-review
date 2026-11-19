"""Make anonymised demo reports from real ones, for README screenshots (development only).

Names of devices, rooms and cars become generic; every number is scaled by a fixed random factor per series, so
the demo looks realistic without showing a real household's figures.

    python dev/demo.py   -> dev/demo/*.html (English) from dev/out/*.json
"""
from __future__ import annotations

import importlib
import json
import random
import sys
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
pkg = types.ModuleType("hir")
pkg.__path__ = [str(ROOT / "custom_components" / "home_in_review")]
sys.modules["hir"] = pkg
render = importlib.import_module("hir.render")

SRC = Path(__file__).resolve().parent / "out"
OUT = Path(__file__).resolve().parent / "demo"
DEVICES = ["Electric car", "Heat pump", "Water heater", "Dishwasher", "Kettle tap", "Home office", "TV and media",
           "Tumble dryer", "Washing machine", "Office 2", "3D printer", "Display cabinet", "Reading lamp", "Heat cable",
           "Backup heater", "Network cupboard", "Space heater"]
ROOMS = ["Utility room", "Hallway", "Office", "Kitchen", "Toilet", "Living room", "Dining room", "Kids room",
         "Walk-in closet", "Landing", "Bedroom", "Bathroom", "Attic", "Guest room"]
STORY = ("A calm, slightly cooler month than last year. The house used about the same electricity, but the solar panels "
         "delivered less as autumn set in, so more came from the grid.\n"
         "The heat pump started its season and did so efficiently, helped by mild days in the first half of the month.")


def main() -> None:
    rnd = random.Random(42)
    factors: dict[str, float] = {}

    def f(key: str) -> float:
        if key not in factors:
            factors[key] = rnd.uniform(0.85, 1.15)
        return factors[key]

    dev_names: dict[str, str] = {}
    room_names: dict[str, str] = {}
    docs = {}
    for p in sorted(SRC.glob("????-??.json")):
        d = json.loads(p.read_text())
        e = d.get("energy") or {}
        for k in ("import", "export", "solar", "battery_charge", "battery_discharge", "consumption", "cost_import",
                  "compensation", "net_cost", "total_cost", "base_load_w", "self_consumed_solar"):
            if isinstance(e.get(k), (int, float)):
                e[k] *= f("e")
        for day in e.get("daily", []):
            for k in ("import", "export", "solar", "load", "cost"):
                day[k] *= f("e")
        e["by_hour_w"] = [v * f("e") if v is not None else None for v in e.get("by_hour_w", [])]
        e["glitch_hours"] = {}
        for x in (d.get("devices") or {}).get("items", []):
            x["name"] = dev_names.setdefault(x["stat"], DEVICES[len(dev_names) % len(DEVICES)])
            x["stat"] = "sensor.demo_" + str(DEVICES.index(x["name"]))
            for k in ("kwh", "value"):
                if isinstance(x.get(k), (int, float)):
                    x[k] *= f("e")
        for k in ("tracked", "untracked"):
            if d.get("devices"):
                d["devices"][k] *= f("e")
        for i, b in enumerate((d.get("batteries") or {}).get("units", [])):
            b["name"] = f"Battery {i + 1}"
        if d.get("heat_pump"):
            d["heat_pump"]["devices"] = ["Heat pump", "Backup heater"]
            for k in ("electricity", "heat"):
                if isinstance(d["heat_pump"].get(k), (int, float)):
                    d["heat_pump"][k] *= f("hp")
        if d.get("car"):
            for c in d["car"]["cars"]:
                c["name"] = "Family car"
                for k in ("km", "charged", "charged_home"):
                    c[k] *= f("car")
            d["car"]["km"] = sum(c["km"] for c in d["car"]["cars"])
        for a in (d.get("indoor") or {}).get("areas", []):
            a["name"] = room_names.setdefault(a["area_id"], ROOMS[len(room_names) % len(ROOMS)])
            a["floor"] = {"Beneden": "Ground floor", "Boven": "First floor"}.get(a.get("floor"), a.get("floor"))
        ind = d.get("indoor")
        if ind and ind.get("areas"):
            t = [a for a in ind["areas"] if "temp" in a]
            ind["warmest"] = max(t, key=lambda a: a["temp"])["name"] if t else None
        s = d.get("indoor_sources")
        if s:
            s["excluded_areas"] = ["Back garden", "Front garden", "Shed"]
            for x in s["dropped"]:
                x["area"] = room_names.get(x.get("area"), "Hallway")
        if d.get("water"):
            d["water"]["amount"] *= f("w")
            d["water"]["per_day"] *= f("w")
        d.pop("custom", None)
        if d.get("story"):
            d["story"] = {"text": STORY, "entity": "ai_task.demo"}
        docs[p.stem] = d
    OUT.mkdir(exist_ok=True)
    for ym in docs:
        (OUT / f"{ym}.html").write_text(render.render_month(ym, docs, "en", "Demo home", 1))
    for k in render.year_keys(docs, 1):
        (OUT / f"year-{k}.html").write_text(render.render_year(k, docs, "en", "Demo home", 1))
    (OUT / "index.html").write_text(render.render_index(docs, "en", "Demo home", "EUR", 1))
    print("demo written to", OUT)


if __name__ == "__main__":
    main()
