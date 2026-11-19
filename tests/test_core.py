import asyncio
from zoneinfo import ZoneInfo

from hir import collector as C
from hir import render as R
from hir.i18n import Lang

TZ = ZoneInfo("Europe/Amsterdam")


def test_month_hours_across_dst():
    a, b = C.month_bounds(2026, 10, TZ)
    assert len(C.hour_starts(a, b)) == 31 * 24 + 1  # October has the extra DST hour
    a, b = C.month_bounds(2026, 3, TZ)
    assert len(C.hour_starts(a, b)) == 31 * 24 - 1


def test_hourly_deltas_gap_glitch_and_reset():
    h0 = 1_000_000_000 - 1_000_000_000 % 3600
    hours = [h0 + i * 3600 for i in range(6)]
    rows = [{"start": h0 - 3600, "sum": 10.0}, {"start": h0, "sum": 11.0},
            # h0+1h missing: the gap goes to the next hour
            {"start": h0 + 7200, "sum": 13.0},
            {"start": h0 + 10800, "sum": 9013.0},   # glitch
            {"start": h0 + 14400, "sum": 9012.0},   # negative step
            {"start": h0 + 18000, "sum": 9013.5}]
    d, glitches = C.hourly_deltas(rows, hours, cap=50)
    assert d[h0] == 1.0
    assert d[h0 + 7200] == 2.0
    assert d[h0 + 10800] == 0.0 and glitches == [h0 + 10800]
    assert d[h0 + 14400] == 0.0
    assert d[h0 + 18000] == 1.5


def test_parse_prefs_old_and_new_grid_format():
    new = {"energy_sources": [
        {"type": "grid", "stat_energy_from": "sensor.t1_in", "stat_energy_to": "sensor.t1_out",
         "entity_energy_price": "sensor.price", "entity_energy_price_export": "sensor.price", "stat_cost": None},
        {"type": "solar", "stat_energy_from": "sensor.pv"},
        {"type": "battery", "stat_energy_from": "sensor.b_out", "stat_energy_to": "sensor.b_in", "name": "B"},
        {"type": "water", "stat_energy_from": "sensor.water", "number_energy_price": 1.3}],
        "device_consumption": [{"stat_consumption": "sensor.dev", "name": "Dev", "included_in_stat": "sensor.parent"}]}
    p = C.parse_energy_prefs(new)
    assert p["imp"] == [{"stat": "sensor.t1_in", "cost": "sensor.t1_in_cost"}]
    assert p["exp"] == [{"stat": "sensor.t1_out", "cost": "sensor.t1_out_compensation"}]
    assert p["battery"][0]["charge"] == "sensor.b_in"
    assert p["water"][0]["cost"] == "sensor.water_cost"
    assert p["devices"][0]["parent"] == "sensor.parent"
    old = {"energy_sources": [{"type": "grid",
                               "flow_from": [{"stat_energy_from": "sensor.a", "stat_cost": "sensor.a_eur"}],
                               "flow_to": [{"stat_energy_to": "sensor.b"}]}]}
    p = C.parse_energy_prefs(old)
    assert p["imp"] == [{"stat": "sensor.a", "cost": "sensor.a_eur"}]
    assert p["exp"] == [{"stat": "sensor.b", "cost": None}]


def test_prefer_room_sensors():
    s = [
        {"entity_id": "t_room", "device_class": "temperature", "device_id": "climate", "area_id": "hall"},
        {"entity_id": "h_room", "device_class": "humidity", "device_id": "climate", "area_id": "hall"},
        {"entity_id": "t_pipe", "device_class": "temperature", "device_id": "pipes", "area_id": "hall"},
        {"entity_id": "t_motion", "device_class": "temperature", "device_id": "motion", "area_id": "toilet"},
        {"entity_id": "t_co2", "device_class": "temperature", "device_id": "mhz19", "area_id": "closet"},
        {"entity_id": "c_co2", "device_class": "carbon_dioxide", "device_id": "mhz19", "area_id": "closet"},
    ]
    kept = {x["entity_id"] for x in C.prefer_room_sensors(s)}
    assert kept == {"t_room", "h_room", "t_motion", "c_co2"}


def test_outdoor_names():
    for name in ("Achtertuin", "Back garden", "Backyard", "Buiten", "Vorgarten", "Balkon"):
        assert C.is_outdoor_name(name), name
    for name in ("Kitchen", "Tuinkamer", "Garage", "Berging", "Buitenkeuken"):
        assert not C.is_outdoor_name(name), name


def test_number_formatting():
    nl, en = Lang("nl"), Lang("en", "USD")
    assert nl.num(1234.5, 1) == "1.234,5"
    assert en.num(1234.5, 1) == "1,234.5"
    assert nl.money(-12.3, 2) == "−€ 12,30"
    assert en.money(12.3, 2) == "$12.30"
    assert Lang("xx").code == "en"


class FakeSource:
    """Two hours of a tiny house: 1 kWh import per hour at 0.30, solar 0.5 kWh."""

    def __init__(self):
        self.prefs = {"energy_sources": [
            {"type": "grid", "stat_energy_from": "sensor.imp", "stat_energy_to": "sensor.exp",
             "entity_energy_price": "sensor.p", "entity_energy_price_export": "sensor.p"},
            {"type": "solar", "stat_energy_from": "sensor.pv"}],
            "device_consumption": [{"stat_consumption": "sensor.dev", "name": "Fridge"}]}

    async def config(self):
        return {"time_zone": "Europe/Amsterdam", "latitude": None, "longitude": None, "currency": "EUR",
                "unit_system": "metric", "language": "en"}

    async def energy_prefs(self):
        return self.prefs

    async def statistics_meta(self, ids):
        return {}

    async def statistics(self, ids, start, end, period, units, types):
        out = {}
        first = int(start.timestamp())
        n = int((end - start).total_seconds() // 3600)
        per_hour = {"sensor.imp": 1.0, "sensor.imp_cost": 0.3, "sensor.exp": 0.2, "sensor.exp_compensation": 0.02,
                    "sensor.pv": 0.5, "sensor.dev": 0.1}
        for i in ids:
            if i in per_hour:
                out[i] = [{"start": first + k * 3600, "sum": per_hour[i] * k} for k in range(n)]
        return out

    async def climate_sensors(self):
        return []

    async def areas(self):
        return [{"area_id": "garden", "name": "Achtertuin", "floor_name": None},
                {"area_id": "sun", "name": "Tuinkamer", "floor_name": None}]

    async def fetch_json(self, url):
        raise OSError("offline")


def test_collect_and_render_offline():
    doc = asyncio.run(C.Collector(FakeSource(), {"fixed_costs_monthly": 10}).collect(2026, 2))
    e = doc["energy"]
    hours = 28 * 24
    assert round(e["import"], 6) == hours * 1.0
    assert round(e["consumption"], 6) == round(hours * (1.0 - 0.2 + 0.5), 6)
    assert round(e["cost_import"], 4) == round(hours * 0.3, 4)
    assert round(e["total_cost"], 4) == round(hours * (0.3 - 0.02) + 10, 4)
    dev = doc["devices"]["items"][0]
    assert dev["name"] == "Fridge"
    assert round(dev["value"], 4) == round(hours * 0.1 * 0.3, 4)  # house imports every hour: import price
    assert "weather" not in doc  # no location
    assert doc["indoor_sources"]["excluded_areas"] == ["Achtertuin"] and doc["indoor_sources"]["excluded_auto"]
    docs = {"2026-02": doc}
    for lang in ("en", "nl"):
        html = R.render_month("2026-02", docs, lang=lang, home_name="Test")
        assert "<svg" in html and ("February" in html or "Februari" in html)
    assert "Februar" in R.render_index(docs, "en")


def test_device_valued_at_export_price_in_export_hours():
    src = FakeSource()
    orig = src.statistics

    async def exporting(ids, start, end, period, units, types):
        out = await orig(ids, start, end, period, units, types)
        n = len(next(iter(out.values())))
        # more export (2 kWh/h at 0.05) than import (1 kWh/h)
        if "sensor.exp" in out:
            out["sensor.exp"] = [{"start": r["start"], "sum": 2.0 * k} for k, r in enumerate(out["sensor.exp"])]
            out["sensor.exp_compensation"] = [{"start": r["start"], "sum": 0.1 * k} for k, r in enumerate(out["sensor.exp"])]
        return out if n else out

    src.statistics = exporting
    doc = asyncio.run(C.Collector(src).collect(2026, 2))
    dev = doc["devices"]["items"][0]
    assert round(dev["value"], 4) == round(28 * 24 * 0.1 * 0.05, 4)


def _year_docs():
    docs = {}
    for m in range(1, 13):
        docs[f"2026-{m:02d}"] = asyncio.run(C.Collector(FakeSource()).collect(2026, m))
    return docs


def test_year_review_and_languages():
    docs = _year_docs()
    assert R.year_keys(docs, 1) == ["2026-01"]
    assert R.year_keys(docs, 7) == ["2025-07", "2026-07"]
    assert R.year_label("2025-07") == "2025/26"
    for lang in ("en", "nl", "de", "fr"):
        html = R.render_year("2026-01", docs, lang, "Test", 1)
        assert "<svg" in html
        assert "{" not in html.split("</head>")[1].split("<script>")[0]  # no unformatted placeholders
        month = R.render_month("2026-05", docs, lang, "Test", 1)
        assert "{" not in month.split("</head>")[1].split("<script>")[0]
    idx = R.render_index(docs, "nl", None, "EUR", 1)
    assert 'data-go="year-2026-01"' in idx


def test_custom_tiles_and_story_facts():
    from hir import story

    src = FakeSource()
    orig = src.statistics

    async def with_power(ids, start, end, period, units, types):
        out = await orig(ids, start, end, period, units, types)
        if "sensor.desk_power" in ids:
            first = int(start.timestamp())
            out["sensor.desk_power"] = [{"start": first + k * 3600, "mean": 50.0 if k % 2 else 2.0} for k in range(48)]
        return out

    src.statistics = with_power
    opts = {"custom_tiles": [{"name": "Desk", "statistic": "sensor.desk_power", "type": "hours_above", "threshold": 12},
                             {"name": "Desk avg", "statistic": "sensor.desk_power", "type": "mean", "decimals": 1}]}
    doc = asyncio.run(C.Collector(src, opts).collect(2026, 2))
    assert doc["custom"][0]["value"] == 24.0
    assert doc["custom"][1]["value"] == 26.0
    f = story.facts(doc)
    assert f["electricity_used_kwh"] == round(28 * 24 * 1.3)
    text = story.instructions("2026-02", {"2026-02": doc}, "nl")
    assert "Dutch" in text and "never invent" in text
