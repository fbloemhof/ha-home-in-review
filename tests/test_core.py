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
    assert Lang("de").money(12.3, 2) == "12,30 €" and Lang("it").money(-5, 0) == "−5 €"
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

    async def names(self, ids):
        return {i: i.split(".")[1].replace("_", " ").title() for i in ids}

    async def device_names(self, ids):
        return await self.names(ids)

    async def areas(self):
        return [{"area_id": "garden", "name": "Achtertuin", "floor_name": None},
                {"area_id": "sun", "name": "Tuinkamer", "floor_name": None}]

    async def fetch_json(self, url, allow_redirects=True):
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
    for lang in ("en", "nl", "de", "fr", "es", "it"):
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
    assert "Dutch" in text and "Do not calculate" in text
    assert "Energy costs: the household paid" in text


def test_any_brand_heat_pump_car_and_single_battery():
    src = FakeSource()
    src.prefs["energy_sources"].append({"type": "battery", "stat_energy_from": "sensor.b_out",
                                        "stat_energy_to": "sensor.b_in", "name": "Home battery"})
    orig = src.statistics

    async def more(ids, start, end, period, units, types):
        out = await orig(ids, start, end, period, units, types)
        first = int(start.timestamp())
        n = int((end - start).total_seconds() // 3600)
        per = {"sensor.hp_kwh": 0.5, "sensor.heat_ch": 1.5, "sensor.heat_dhw": 0.5, "sensor.charger": 0.25,
               "sensor.b_in": 0.2, "sensor.b_out": 0.18}
        for i in ids:
            if i in per:
                out[i] = [{"start": first + k * 3600, "sum": per[i] * k} for k in range(n)]
        if "sensor.odometer" in ids:  # 10 km a day
            out["sensor.odometer"] = [{"start": first + k * 3600, "max": 20000 + k * 10 / 24, "mean": None} for k in range(n)]
        return out

    src.statistics = more
    opts = {"heat_pump_devices": ["sensor.hp_kwh"], "heat_pump_heat_sensor": ["sensor.heat_ch", "sensor.heat_dhw"],
            "car_odometers": ["sensor.odometer"], "car_chargers": ["sensor.charger"]}
    doc = asyncio.run(C.Collector(src, opts).collect(2026, 2))
    assert round(doc["heat_pump"]["cop"], 2) == 4.0
    assert doc["heat_pump"]["devices"] == ["Hp Kwh"]
    car = doc["car"]
    assert car["source"] == "sensors" and 270 < car["km"] < 290  # 28 days x 10 km, measured from the month start
    assert round(car["charged_home"]) == 28 * 24 * 0.25
    html = R.render_month("2026-02", {"2026-02": doc}, "nl", None, 1)
    assert "De batterij sloeg" in html and "De auto reed" in html and "COP" in html


def test_days_above_rain_gauge_and_evcc():
    src = FakeSource()
    orig = src.statistics

    async def more(ids, start, end, period, units, types):
        out = await orig(ids, start, end, period, units, types)
        first = int(start.timestamp())
        n = int((end - start).total_seconds() // 3600)
        if "sensor.stove" in ids:  # burning 19-23h on even days
            out["sensor.stove"] = [{"start": first + k * 3600, "mean": 1.0 if (k // 24) % 2 == 0 and 19 <= k % 24 < 23 else 0.0}
                                   for k in range(n)]
        if "sensor.rain" in ids:  # 1 mm every 6 hours
            out["sensor.rain"] = [{"start": first + k * 3600, "sum": (k // 6) * 1.0} for k in range(n)]
        return out

    sessions = [
        {"created": "2026-02-03T20:00:00+01:00", "vehicle": "Car A", "chargedEnergy": 30, "price": 6.0, "solarPercentage": 0, "odometer": 10000},
        {"created": "2026-02-10T12:00:00+01:00", "vehicle": "Car A", "chargedEnergy": 20, "price": 1.0, "solarPercentage": 100, "odometer": 10500},
        {"created": "2026-03-01T12:00:00+01:00", "vehicle": "Car A", "chargedEnergy": 99},  # next month, ignored
    ]

    async def fetch(url, allow_redirects=True):
        assert allow_redirects is False  # evcc requests never follow redirects
        if "/api/sessions" in url:
            return {"result": sessions}  # older evcc wraps the list
        raise OSError("offline")

    src.statistics = more
    src.fetch_json = fetch
    opts = {"custom_tiles": [{"name": "Stove", "statistic": "sensor.stove", "type": "days_above", "threshold": 0.5}],
            "rain_sensor": "sensor.rain", "evcc_url": "http://evcc.local:7070"}
    doc = asyncio.run(C.Collector(src, opts).collect(2026, 2))
    assert doc["custom"][0]["value"] == 14.0 and doc["custom"][0]["unit"] == "days"
    car = doc["car"]
    assert car["source"] == "evcc" and car["sessions"] == 2 and car["charged"] == 50
    assert round(car["cost"], 2) == 7.0 and round(car["solar_share"], 2) == 0.4 and car["km"] == 500
    html = R.render_month("2026-02", {"2026-02": doc}, "nl", None, 1)
    import re
    text = re.sub(r"<[^>]+>", "", html)
    assert "zonnestroom" in text, re.findall(r"Er werd.{0,120}", text)
    assert re.search(r"Stove\s*14\s*dagen", text), re.findall(r"Stove.{0,60}", text)


def test_count_runs():
    from hir.extras import count_runs

    h = 3600
    # a 2-hour run, a pause of 4 hours, a 1-hour run with a 1-hour pause inside, and a 7-hour block
    active = [0, h, 6 * h, 8 * h, 20 * h, 21 * h, 22 * h, 23 * h, 24 * h, 25 * h, 26 * h]
    assert len(count_runs(active, None)) == 3
    assert len(count_runs(active, 3)) == 4  # 2 h + 3 h blocks count once, the 7-hour block as two programmes
    assert count_runs([], 3) == []


def test_gas_split():
    from hir import gas

    dd = [float(x % 15) for x in range(30)]            # 0..14 degree days, plenty of spread
    use = [0.5 + 0.3 * x for x in dd]                   # base 0.5 per day, 0.3 per degree day
    r = gas.split(use, dd)
    assert r["base_source"] == "estimate" and abs(r["base_per_day"] - 0.5) < 1e-9
    assert abs(r["hot_water"] - 15) < 1e-6 and abs(r["heating"] - (sum(use) - 15)) < 1e-6
    assert abs(r["heating_per_degree_day"] - 0.3) < 1e-9
    r = gas.split(use, dd, base_per_day=0.4)            # the option wins
    assert r["base_source"] == "option" and abs(r["hot_water"] - 12) < 1e-9
    summer = gas.split([0.6] * 30, [0.2] * 30)
    assert summer["base_source"] == "no_heating" and summer["heating"] == 0
    flat = gas.split([3.0] * 30, [8.0] * 30)            # no spread: no reliable split
    assert flat["base_source"] == "unknown" and "heating" not in flat and flat["per_degree_day"] == 3 / 8
    assert gas.split([], []) is None


def test_year_status():
    docs = {f"2025-{m:02d}": {} for m in (11, 12)} | {f"2026-{m:02d}": {} for m in range(1, 11)}
    assert R.year_status("2025-01", docs) == "incomplete"   # over, but only Nov and Dec
    assert R.year_status("2026-01", docs) == "running"      # Jan-Oct, the year isn't over yet
    full = {f"2025-{m:02d}": {} for m in range(1, 13)}
    assert R.year_status("2025-01", full) == "complete"
    nl = Lang("nl")
    assert R.year_note(nl, "2025-01", docs) == "2 van 12 maanden"
    assert R.year_note(nl, "2026-01", docs) == "10 van 12 maanden tot nu toe"


def test_trend_bars_link_to_months():
    docs = _year_docs()
    html = R.render_month("2026-05", docs, "en", None, 1)
    assert 'data-go="2026-04"' in html and 'data-go="2026-01"' in html   # earlier months are links
    year = R.render_year("2026-01", docs, "en", None, 1)
    assert 'data-go="2026-07"' in year                                      # year bars open the month


def test_degree_day_options():
    from hir import weather

    days = [{"d": f"2026-10-{i:02d}", "mean": 12.0, "min": 8.0, "max": 16.0, "precip": 0, "sun_h": 3} for i in range(1, 32)]
    plain = weather.summarize(days, None, 10, True)
    assert plain["degree_days"] == 31 * 6 and plain["dd_base"] == 18.0
    nov = [{**d, "d": d["d"].replace("-10-", "-11-")} for d in days[:30]]
    assert round(weather.summarize(nov, None, 11, True, dd_weighted=True)["degree_days"], 6) == round(30 * 6 * 1.1, 6)
    assert weather.summarize(days, None, 10, True, dd_base=20)["degree_days"] == 31 * 8
    us = weather.summarize(days, None, 10, False)        # 12 °C = 53.6 °F, threshold 65 °F
    assert round(us["degree_days"], 6) == round(31 * (65 - 53.6), 6)


def test_weather_note_says_where():
    from hir import weather

    days = [{"d": f"2026-02-{i:02d}", "mean": 4.0, "min": 1.0, "max": 7.0, "precip": 1, "sun_h": 2} for i in range(1, 29)]
    doc = asyncio.run(C.Collector(FakeSource()).collect(2026, 2))
    doc["weather"] = {**weather.summarize(days, None, 2, True), "source": "open-meteo", "location": {"lat": 52.1, "lon": 5.2}}
    html = R.render_month("2026-02", {"2026-02": doc}, "nl", None, 1)
    assert "omgeving van 52,1° N, 5,2° E" in html and "stookgrens 18 °C" in html
    doc["weather"].update(source="sensor", sensor_name="Tuinsensor")
    html = R.render_month("2026-02", {"2026-02": doc}, "nl", None, 1)
    assert "Buitensensor: Tuinsensor." in html and "52,1° N" in html
