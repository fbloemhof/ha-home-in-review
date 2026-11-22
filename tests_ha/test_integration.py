"""Setup, report access (authentication, signed paths, administrators only), options and unload."""
from __future__ import annotations

from homeassistant.components import frontend
from homeassistant.config_entries import SOURCE_USER
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.home_in_review.const import DOMAIN, PANEL_URL

DOC = {
    "schema": 1,
    "period": {"year": 2026, "month": 10, "start": "2026-10-01T00:00:00+02:00", "end": "2026-11-01T00:00:00+01:00",
               "hours": 745, "time_zone": "Europe/Amsterdam"},
    "generated": "2026-11-01T07:00+01:00",
    "units": {"energy": "kWh", "currency": "EUR", "temperature": "°C", "water": "L", "gas": "m³"},
    "notes": [],
    "devices": {"items": [{"name": "<script>alert(1)</script>", "stat": "sensor.x", "parent": None, "kwh": 5.0,
                           "value": 1.0, "share": 0.5, "partial": False, "glitch_hours": 0, "no_data": False}],
                "tracked": 5.0, "untracked": 5.0, "untracked_share": 0.5},
    "energy": {"import": 10.0, "export": 0.0, "solar": 0.0, "battery_charge": 0.0, "battery_discharge": 0.0,
               "consumption": 10.0, "daily": [{"d": "2026-10-01", "import": 10.0, "export": 0.0, "solar": 0.0,
                                               "load": 10.0, "cost": 3.0}],
               "by_hour_w": [400.0] * 24, "glitch_hours": {}},
    "sections": ["energy", "devices"],
}


async def setup_entry(hass: HomeAssistant, options: dict | None = None) -> MockConfigEntry:
    entry = MockConfigEntry(domain=DOMAIN, data={"backfill_months": 0}, options=options or {})
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    entry.runtime_data.store.docs["2026-10"] = DOC
    return entry


async def test_config_flow(recorder_mock, hass: HomeAssistant) -> None:
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})
    assert result["type"] is FlowResultType.FORM
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {"backfill_months": 0})
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"] == {"backfill_months": 0}
    # single instance
    again = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})
    assert again["type"] is FlowResultType.ABORT


async def test_report_requires_login(recorder_mock, hass: HomeAssistant, hass_client, hass_client_no_auth) -> None:
    await setup_entry(hass)
    anon = await hass_client_no_auth()
    assert (await anon.get("/api/home_in_review/report/2026-10")).status == 401
    client = await hass_client()
    resp = await client.get("/api/home_in_review/report/2026-10")
    assert resp.status == 200
    assert "default-src 'none'" in resp.headers["Content-Security-Policy"]
    html = await resp.text()
    assert "<script>alert(1)</script>" not in html and "&lt;script&gt;alert(1)&lt;/script&gt;" in html
    assert (await client.get("/api/home_in_review/report/index")).status == 200
    assert (await client.get("/api/home_in_review/report/2025-01")).status == 404
    assert (await client.get("/api/home_in_review/report/..%2F..%2Fsecrets")).status in (400, 404)


async def test_report_latest(recorder_mock, hass: HomeAssistant, hass_client) -> None:
    entry = await setup_entry(hass)
    client = await hass_client()
    resp = await client.get("/api/home_in_review/report/latest")
    assert resp.status == 200
    assert await resp.text() == await (await client.get("/api/home_in_review/report/2026-10")).text()
    entry.runtime_data.store.docs.clear()
    assert (await client.get("/api/home_in_review/report/latest")).status == 404


async def test_signed_path(recorder_mock, hass: HomeAssistant, hass_ws_client, hass_client_no_auth) -> None:
    await setup_entry(hass)
    ws = await hass_ws_client(hass)
    await ws.send_json({"id": 1, "type": "auth/sign_path", "path": "/api/home_in_review/report/2026-10", "expires": 30})
    msg = await ws.receive_json()
    assert msg["success"], msg
    anon = await hass_client_no_auth()
    assert (await anon.get(msg["result"]["path"])).status == 200
    # a signature for one report doesn't open another
    other = msg["result"]["path"].replace("2026-10", "index")
    assert (await anon.get(other)).status == 401


async def test_admin_only(recorder_mock, hass: HomeAssistant, hass_client, hass_read_only_access_token) -> None:
    await setup_entry(hass, {"admin_only": True})
    admin = await hass_client()
    assert (await admin.get("/api/home_in_review/report/2026-10")).status == 200
    user = await hass_client(hass_read_only_access_token)
    assert (await user.get("/api/home_in_review/report/2026-10")).status == 403
    assert hass.data[frontend.DATA_PANELS][PANEL_URL].require_admin is True


async def test_everyone_by_default(recorder_mock, hass: HomeAssistant, hass_client, hass_read_only_access_token) -> None:
    await setup_entry(hass)
    user = await hass_client(hass_read_only_access_token)
    assert (await user.get("/api/home_in_review/report/2026-10")).status == 200


SETTINGS = {
    "general": {"report_day": 1, "report_time": "07:00:00", "year_start_month": "1", "admin_only": False},
    "energy": {"max_hourly_kwh": 25},
    "climate": {"use_open_meteo": True},
    "car": {},
    "ai": {},
}


async def test_options_url_validation(recorder_mock, hass: HomeAssistant) -> None:
    entry = await setup_entry(hass)

    async def submit(car: dict):
        flow = await hass.config_entries.options.async_init(entry.entry_id)
        assert flow["type"] is FlowResultType.MENU
        form = await hass.config_entries.options.async_configure(flow["flow_id"], {"next_step_id": "settings"})
        assert form["type"] is FlowResultType.FORM
        return await hass.config_entries.options.async_configure(form["flow_id"], {**SETTINGS, "car": car})

    bad = await submit({"teslamate_grafana_url": "http://grafana.example.com", "teslamate_grafana_token": "x"})
    assert bad["type"] is FlowResultType.FORM and bad["errors"] == {"car": "https_required"}
    bad = await submit({"teslamate_grafana_url": "https://user:pw@grafana.example.com", "teslamate_grafana_token": "x"})
    assert bad["errors"] == {"car": "url_credentials"}
    bad = await submit({"evcc_url": "file:///etc/passwd"})
    assert bad["errors"] == {"car": "invalid_url"}
    bad = await submit({"teslamate_grafana_url": "https://grafana.example.com"})
    assert bad["errors"] == {"car": "teslamate_incomplete"}
    ok = await submit({"teslamate_grafana_url": "http://192.168.1.20:3000", "teslamate_grafana_token": "x",
                       "evcc_url": "http://evcc.local:7070"})
    assert ok["type"] is FlowResultType.CREATE_ENTRY
    await hass.async_block_till_done()
    assert entry.options["evcc_url"] == "http://evcc.local:7070"


async def test_tile_add_requires_statistic(recorder_mock, hass: HomeAssistant) -> None:
    entry = await setup_entry(hass)
    flow = await hass.config_entries.options.async_init(entry.entry_id)
    form = await hass.config_entries.options.async_configure(flow["flow_id"], {"next_step_id": "tile_add"})
    res = await hass.config_entries.options.async_configure(form["flow_id"], {"name": "Test", "type": "sum", "decimals": 0})
    assert res["type"] is FlowResultType.FORM and res["errors"] == {"statistic": "statistic_required"}


async def test_unload_removes_panel(recorder_mock, hass: HomeAssistant) -> None:
    entry = await setup_entry(hass)
    assert PANEL_URL in hass.data[frontend.DATA_PANELS]
    assert hass.services.has_service(DOMAIN, "generate")
    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()
    assert PANEL_URL not in hass.data[frontend.DATA_PANELS]


def test_default_backfill_covers_last_year() -> None:
    import datetime as dt

    from custom_components.home_in_review.config_flow import default_backfill_months

    assert default_backfill_months(dt.date(2026, 11, 19)) == 22   # Jan 2025 .. Oct 2026
    assert default_backfill_months(dt.date(2026, 1, 5)) == 12     # all of 2025


async def test_stale_reports_are_refreshed(recorder_mock, hass: HomeAssistant) -> None:
    """A report made by an older version (no fingerprint) is re-made in the background after setup."""
    import json
    from pathlib import Path

    store = Path(hass.config.path("home_in_review"))
    await hass.async_add_executor_job(lambda: store.mkdir(exist_ok=True))
    old = {**DOC, "period": {**DOC["period"], "year": 2026, "month": 9}}
    await hass.async_add_executor_job((store / "2026-09.json").write_text, json.dumps(old))
    entry = MockConfigEntry(domain=DOMAIN, data={"backfill_months": 0, "backfilled": True})
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done(wait_background_tasks=True)
    rt = entry.runtime_data
    assert rt.store.docs["2026-09"]["meta"]["fingerprint"] == rt.fingerprint()
    assert rt.stale_months() == []


async def test_ai_summary_reused_when_figures_unchanged(recorder_mock, hass: HomeAssistant) -> None:
    entry = await setup_entry(hass, {"ai_task_entity": "ai_task.test"})
    rt = entry.runtime_data
    calls = []

    async def fake_ai(entity, prompt):
        calls.append(prompt)
        return "A calm month."

    rt.source.ai_generate = fake_ai
    first = {**DOC}
    await rt._story("2026-10", first)
    assert first["story"]["text"] == "A calm month." and len(calls) == 1
    second = {**DOC}
    await rt._story("2026-10", second, previous=first)
    assert second["story"] == first["story"] and len(calls) == 1      # same figures: no new AI call
    changed = {**DOC, "energy": {**DOC["energy"], "consumption": 99.0}}
    await rt._story("2026-10", changed, previous=first)
    assert len(calls) == 2                                              # figures changed: written again


async def test_boiler_on_time_sensors(recorder_mock, hass: HomeAssistant, freezer) -> None:
    """The on-time sensors add up the hours the boiler status was active, survive option changes, and are
    handed to the collector."""
    from homeassistant.helpers import entity_registry as er

    freezer.move_to("2026-11-19 10:00:00+00:00")
    hass.states.async_set("binary_sensor.boiler_dhw", "off")
    hass.states.async_set("climate.thermostat", "heat", {"hvac_action": "idle"})
    entry = await setup_entry(hass, {"gas_hot_water_active": "binary_sensor.boiler_dhw",
                                     "gas_heating_active": "climate.thermostat"})
    reg = er.async_get(hass)
    dhw = reg.async_get_entity_id("sensor", DOMAIN, f"{entry.entry_id}_hot_water_time")
    ch = reg.async_get_entity_id("sensor", DOMAIN, f"{entry.entry_id}_heating_time")
    assert dhw and ch
    assert entry.runtime_data.boiler_stats() == {"dhw": dhw, "ch": ch}

    hass.states.async_set("binary_sensor.boiler_dhw", "on")
    hass.states.async_set("climate.thermostat", "heat", {"hvac_action": "heating"})
    await hass.async_block_till_done()
    freezer.tick(1800)  # half an hour
    hass.states.async_set("binary_sensor.boiler_dhw", "off")
    await hass.async_block_till_done()
    assert abs(float(hass.states.get(dhw).state) - 0.5) < 0.01
    freezer.tick(1800)  # heating keeps running: an hour in total
    hass.states.async_set("climate.thermostat", "heat", {"hvac_action": "idle"})
    await hass.async_block_till_done()
    assert abs(float(hass.states.get(ch).state) - 1.0) < 0.01
    assert hass.states.get(dhw).attributes["state_class"] == "total_increasing"

    # Clearing an option removes its sensor.
    hass.config_entries.async_update_entry(entry, options={"gas_hot_water_active": "binary_sensor.boiler_dhw"})
    await hass.async_block_till_done()
    assert reg.async_get_entity_id("sensor", DOMAIN, f"{entry.entry_id}_heating_time") is None
    assert hass.states.get(dhw) is not None


def test_unreachable_service_keeps_previous_car() -> None:
    """A temporarily unreachable TeslaMate must not wipe the car from an existing report; the month is retried."""
    from custom_components.home_in_review import keep_previous

    previous = {"car": {"source": "teslamate", "km": 1643}, "sections": ["energy", "car"]}
    doc = {"energy": {"x": 1}, "notes": ["teslamate_unavailable"], "meta": {"fingerprint": "abc"}, "sections": ["energy"]}
    keep_previous(doc, previous)
    assert doc["car"]["km"] == 1643 and doc["sections"] == ["energy", "car"]
    assert doc["meta"]["fingerprint"] is None and doc["notes"] == []
    fresh = {"energy": {"x": 1}, "notes": [], "meta": {"fingerprint": "abc"}, "sections": ["energy"]}
    keep_previous(fresh, previous)  # no failure: nothing is carried over
    assert "car" not in fresh and fresh["meta"]["fingerprint"] == "abc"


async def test_gas_summer_base(recorder_mock, hass: HomeAssistant) -> None:
    entry = await setup_entry(hass)
    rt = entry.runtime_data
    for ym, per_day, src in (("2026-06", 0.3, "no_heating"), ("2026-07", 0.25, "no_heating"),
                             ("2026-08", 0.35, "no_heating"), ("2026-09", 0.9, "estimate"), ("2026-12", 0.1, "no_heating")):
        rt.store.docs[ym] = {"gas": {"per_day": per_day, "base_source": src}}
    assert rt.gas_summer_base("2026-11") == 0.3  # median of earlier months without heating; later months ignored
    assert rt.gas_summer_base("2026-05") is None
