"""Optional short written summary of a month, by the user's own AI Task entity.

The model gets only the figures that are in the report (and the same figures for the comparison month), never
entity names or raw data, and is told not to invent anything. The text is labelled as AI-written in the report.
"""
from __future__ import annotations

from .render import prev_ym

LANG_NAMES = {"en": "English", "nl": "Dutch", "de": "German", "fr": "French", "es": "Spanish", "it": "Italian"}


def facts(doc: dict) -> dict:
    """The headline figures of a month document, rounded, with the unit in every key so a model can't mix them up."""
    e = doc.get("energy") or {}
    w = doc.get("weather") or {}
    ind = doc.get("indoor") or {}
    hp = doc.get("heat_pump") or {}
    u = doc.get("units") or {}
    cur = (u.get("currency") or "EUR").lower()
    t = "c" if u.get("temperature", "°C") == "°C" else "f"
    r = lambda v, n=0: None if v is None else round(v, n)  # noqa: E731
    water = doc.get("water") or {}
    gas = doc.get("gas") or {}
    out = {
        "electricity_used_kwh": r(e.get("consumption")), "grid_import_kwh": r(e.get("import")),
        "grid_export_kwh": r(e.get("export")), "solar_production_kwh": r(e.get("solar")),
        "self_sufficiency_percent": r(e["self_sufficiency"] * 100) if e.get("self_sufficiency") is not None else None,
        f"energy_cost_{cur}": r(e.get("total_cost"), 2), "base_load_watt": r(e.get("base_load_w")),
        f"outside_temperature_{t}": r(w.get("temp"), 1), f"normal_outside_temperature_{t}": r((w.get("normal") or {}).get("temp"), 1),
        f"precipitation_{w.get('precip_unit', 'mm')}": r(w.get("precip")), "sunshine_hours": r(w.get("sun_h")),
        f"indoor_temperature_{t}": r(ind.get("temp"), 1), "indoor_humidity_percent": r(ind.get("humidity")),
        "heat_pump_electricity_kwh": r(hp.get("electricity")), "heat_pump_heat_delivered_kwh": r(hp.get("heat")),
        "heat_pump_cop": r(hp.get("cop"), 1), "car_km": r((doc.get("car") or {}).get("km")),
        "water_litres" if water.get("unit") == "L" else f"water_{water.get('unit', '')}": r(water.get("amount")),
        f"gas_{gas.get('unit', '')}": r(gas.get("amount"), 1),
    }
    items = [x for x in (doc.get("devices") or {}).get("items", []) if not x.get("no_data") and not x.get("parent")]
    out["biggest_devices_kwh"] = {x["name"]: r(x["kwh"]) for x in items[:4]} or None
    return {k: v for k, v in out.items() if v not in (None, {}, 0) and not k.endswith("_")}


def _pct(a: float, b: float) -> str:
    p = (a - b) / abs(b) * 100
    if abs(p) < 3:
        return "about the same as"
    return f"{abs(p):.0f}% {'more' if p > 0 else 'less'} than"


def observations(ym: str, docs: dict[str, dict]) -> list[str]:
    """Plain, pre-computed statements in English. The model only chooses and phrases them; it never calculates."""
    doc = docs[ym]
    cur = (doc.get("units") or {}).get("currency", "EUR")
    tu = (doc.get("units") or {}).get("temperature", "°C")
    refs = [("the previous month", docs.get(prev_ym(ym, 1))), ("the same month last year", docs.get(prev_ym(ym, 12)))]
    refs = [(n, facts(d)) for n, d in refs if d]
    f = facts(doc)
    out = []

    def compare(label: str, key: str, unit: str, nd: int = 0, absolute: bool = False) -> None:
        if key not in f:
            return
        v = f[key]
        parts = [f"{label}: {v:.{nd}f} {unit}".strip()]
        for name, rf in refs:
            if rf.get(key):
                if absolute:  # temperatures: a difference in degrees, not a percentage
                    d = v - rf[key]
                    rel = "about the same as" if abs(d) < 0.3 else f"{abs(d):.1f} {unit} {'higher' if d > 0 else 'lower'} than"
                else:
                    rel = _pct(v, rf[key])
                parts.append(f"{rel} {name} ({rf[key]:.{nd}f} {unit})".strip())
        out.append(", ".join(parts) + ".")

    def money(v: float) -> str:
        return f"earned {abs(v):.0f} {cur} (income, not a cost)" if v < 0 else f"paid {v:.0f} {cur}"

    compare("Electricity used in the house", "electricity_used_kwh", "kWh")
    ck = f"energy_cost_{cur.lower()}"
    if ck in f:
        line = ("Energy result: the household made money on energy this month, it " if f[ck] < 0
                else "Energy costs: the household ") + f"{money(f[ck])} this month"
        line += "".join(f"; {name}: {money(rf[ck])}" for name, rf in refs if ck in rf)
        out.append(line + ".")
    compare("Solar production", "solar_production_kwh", "kWh")
    compare("Sunshine", "sunshine_hours", "hours")
    if "self_sufficiency_percent" in f:
        out.append(f"Self-sufficiency: {f['self_sufficiency_percent']:.0f}% of the electricity came from own solar/battery.")
    t = next((k for k in f if k.startswith("outside_temperature_")), None)
    n = next((k for k in f if k.startswith("normal_outside_temperature_")), None)
    if t:
        line = f"Average outside temperature: {f[t]:.1f} {tu}"
        if n:
            d = f[t] - f[n]
            line += (f", {abs(d):.1f} {tu} {'warmer' if d > 0 else 'colder'} than normal ({f[n]:.1f} {tu})"
                     if abs(d) >= 0.5 else f", close to normal ({f[n]:.1f} {tu})")
        out.append(line + ".")
    p = next((k for k in f if k.startswith("precipitation_")), None)
    if p:
        compare("Precipitation", p, p.rsplit("_", 1)[1])
    if "heat_pump_electricity_kwh" in f:
        line = f"The heat pump used {f['heat_pump_electricity_kwh']:.0f} kWh of electricity"
        if "heat_pump_heat_delivered_kwh" in f:
            line += f" and delivered {f['heat_pump_heat_delivered_kwh']:.0f} kWh of heat (COP {f['heat_pump_cop']:.1f}"
            line += "".join(f"; {name}: COP {rf['heat_pump_cop']:.1f}" for name, rf in refs if rf.get("heat_pump_cop")) + ")"
        out.append(line + ".")
    compare("Indoor temperature", next((k for k in f if k.startswith("indoor_temperature_")), "-"), tu, 1, absolute=True)
    gd = doc.get("gas") or {}
    if gd.get("per_degree_day"):
        line = f"Gas per heating degree day: {gd['per_degree_day']:.2f} {gd.get('unit', '')}"
        if gd.get("heating") is not None:
            line += f"; of the gas, {gd['heating']:.0f} {gd.get('unit', '')} went to heating and {gd['hot_water']:.0f} to hot water and cooking"
        out.append(line + ".")
    compare("Water used", "water_litres", "litres")
    compare("Car", "car_km", "km")
    if f.get("biggest_devices_kwh"):
        out.append("Biggest separately measured users: " + ", ".join(f"{k} {v:.0f} kWh" for k, v in f["biggest_devices_kwh"].items()) + ".")
    return out


def instructions(ym: str, docs: dict[str, dict], lang: str, extra: str | None = None) -> str:
    language = LANG_NAMES.get((lang or "en").split("-")[0], "English")
    text = (
        f"Below are verified observations about a household's month. Write a short, friendly summary of them in "
        f"{language} for the people who live there: two short paragraphs, at most 100 words in total, plain text "
        "without headings, lists or emoji. Pick the three or four most notable observations. Use only what is stated "
        "below, with the same numbers (rounded is fine) and the same direction (more/less, paid/earned, warmer/colder). "
        "Do not calculate anything yourself, do not add causes, intentions, advice, praise or judgement; keep a calm, "
        "neutral tone.\n\nObservations:\n- "
        + "\n- ".join(observations(ym, docs))
    )
    if extra:
        text += "\n\nAdditional instructions from the household: " + extra
    return text
