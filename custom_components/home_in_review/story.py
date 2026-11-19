"""Optional short written summary of a month, by the user's own AI Task entity.

The model gets only the figures that are in the report (and the same figures for the comparison month), never
entity names or raw data, and is told not to invent anything. The text is labelled as AI-written in the report.
"""
from __future__ import annotations

import json

from .render import prev_ym

LANG_NAMES = {"en": "English", "nl": "Dutch", "de": "German", "fr": "French"}


def facts(doc: dict) -> dict:
    """The headline figures of a month document, rounded."""
    e = doc.get("energy") or {}
    w = doc.get("weather") or {}
    ind = doc.get("indoor") or {}
    r = lambda v, n=0: None if v is None else round(v, n)  # noqa: E731
    out = {
        "electricity_used_kwh": r(e.get("consumption")), "grid_import_kwh": r(e.get("import")),
        "grid_export_kwh": r(e.get("export")), "solar_kwh": r(e.get("solar")),
        "self_sufficiency_pct": r((e.get("self_sufficiency") or 0) * 100) if e.get("self_sufficiency") is not None else None,
        "energy_cost": r(e.get("total_cost"), 2), "base_load_w": r(e.get("base_load_w")),
        "top_devices": [{"name": x["name"], "kwh": r(x["kwh"])} for x in (doc.get("devices") or {}).get("items", [])
                        if not x.get("no_data") and not x.get("parent")][:4],
        "outside_temp": r(w.get("temp"), 1), "normal_temp": r((w.get("normal") or {}).get("temp"), 1),
        "precipitation": r(w.get("precip")), "sunshine_hours": r(w.get("sun_h")),
        "indoor_temp": r(ind.get("temp"), 1), "indoor_humidity_pct": r(ind.get("humidity")),
        "heat_pump_kwh": r((doc.get("heat_pump") or {}).get("electricity")),
        "car_km": r((doc.get("car") or {}).get("km")),
        "water": r((doc.get("water") or {}).get("amount")), "gas": r((doc.get("gas") or {}).get("amount"), 1),
    }
    return {k: v for k, v in out.items() if v not in (None, [], 0)}


def instructions(ym: str, docs: dict[str, dict], lang: str, extra: str | None = None) -> str:
    doc = docs[ym]
    u = doc["units"]
    ly = docs.get(prev_ym(ym, 12))
    prev = docs.get(prev_ym(ym, 1))
    data = {"month": ym, "units": u, "this_month": facts(doc)}
    if ly:
        data["same_month_last_year"] = facts(ly)
    if prev:
        data["previous_month"] = facts(prev)
    language = LANG_NAMES.get((lang or "en").split("-")[0], "English")
    text = (
        f"Write a short summary of how this household's month went, in {language}, for the people who live there. "
        "Use two short paragraphs, at most 110 words in total, plain text without headings, lists or emoji. "
        "Mention what stood out compared with last year or last month, and connect causes where the data shows them "
        "(for example weather and heating, sunshine and solar). Use only the figures below; never invent numbers, "
        "devices or reasons. Round numbers. Do not give advice unless something is clearly unusual. "
        f"Currency: {u.get('currency')}; temperatures in {u.get('temperature')}.\n\n"
        + json.dumps(data, ensure_ascii=False)
    )
    if extra:
        text += "\n\nAdditional instructions from the household: " + extra
    return text
