"""Home in Review: a monthly report of your home, built from data Home Assistant already has.

- Collects a month from the energy dashboard, Open-Meteo weather and indoor climate sensors (collector.py).
- Stores one JSON document per month in <config>/home_in_review/.
- Serves the reports as HTML, rendered on request (render.py), only to logged-in users.
- Adds a sidebar panel, a monthly schedule with optional notifications, and generate/backfill actions.
"""
from __future__ import annotations

import asyncio
import datetime as dt
import json
import logging
import re
from pathlib import Path
from typing import Any

import voluptuous as vol
from aiohttp import web
from homeassistant.components import frontend, panel_custom
from homeassistant.components.http import HomeAssistantView, StaticPathConfig
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EVENT_HOMEASSISTANT_STARTED
from homeassistant.core import HomeAssistant, ServiceCall, SupportsResponse, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.event import async_track_time_change
from homeassistant.util import dt as dt_util

from . import render, story
from .collector import Collector, first_month
from .const import (
    CONF_AI_INSTRUCTIONS,
    CONF_AI_TASK,
    CONF_BACKFILL_MONTHS,
    CONF_NOTIFY,
    CONF_REPORT_DAY,
    CONF_REPORT_TIME,
    CONF_YEAR_START,
    DEFAULT_BACKFILL_MONTHS,
    DEFAULT_REPORT_DAY,
    DEFAULT_REPORT_TIME,
    DOMAIN,
    PANEL_URL,
    STATIC_URL,
    STORAGE_DIR,
    URL_BASE,
)
from .hass_source import HassSource
from .i18n import Lang

_LOGGER = logging.getLogger(__name__)
CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)
YM = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")
FRONTEND = Path(__file__).parent / "frontend"


def prev_month(today: dt.date) -> tuple[int, int]:
    first = today.replace(day=1) - dt.timedelta(days=1)
    return first.year, first.month


class ReportStore:
    """Month documents on disk, with an in-memory copy for rendering."""

    def __init__(self, hass: HomeAssistant) -> None:
        self.hass = hass
        self.dir = Path(hass.config.path(STORAGE_DIR))
        self.docs: dict[str, dict] = {}
        self.cache: dict[str, Any] = {}

    def _load(self) -> None:
        self.dir.mkdir(exist_ok=True)
        for p in self.dir.glob("????-??.json"):
            try:
                self.docs[p.stem] = json.loads(p.read_text(encoding="utf-8"))
            except (OSError, ValueError) as err:
                _LOGGER.warning("Skipping unreadable report %s: %s", p, err)
        cache = self.dir / "cache.json"
        if cache.exists():
            try:
                self.cache = json.loads(cache.read_text(encoding="utf-8"))
            except ValueError:
                self.cache = {}

    async def async_load(self) -> None:
        await self.hass.async_add_executor_job(self._load)

    async def async_save(self, ym: str, doc: dict) -> None:
        self.docs[ym] = doc
        text = json.dumps(doc, ensure_ascii=False, indent=1)
        cache = json.dumps(self.cache)

        def write() -> None:
            self.dir.mkdir(exist_ok=True)
            (self.dir / f"{ym}.json").write_text(text, encoding="utf-8")
            (self.dir / "cache.json").write_text(cache, encoding="utf-8")

        await self.hass.async_add_executor_job(write)


class HomeInReview:
    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self.hass = hass
        self.entry = entry
        self.store = ReportStore(hass)
        self.source = HassSource(hass)
        self.lock = asyncio.Lock()
        self.backfill_task: asyncio.Task | None = None
        self.loaded_options = dict(entry.options)

    @property
    def options(self) -> dict:
        return {**self.entry.data, **self.entry.options}

    async def generate(self, year: int, month: int) -> dict:
        ym = f"{year:04d}-{month:02d}"
        async with self.lock:
            doc = await Collector(self.source, self.options, self.store.cache).collect(year, month)
            await self._story(ym, doc)
            await self.store.async_save(ym, doc)
            return doc

    async def _story(self, ym: str, doc: dict) -> None:
        """Optional AI-written summary through the user's own AI Task entity."""
        entity = self.options.get(CONF_AI_TASK)
        if not entity:
            return
        docs = {**self.store.docs, ym: doc}
        prompt = story.instructions(ym, docs, self.hass.config.language, self.options.get(CONF_AI_INSTRUCTIONS))
        try:
            text = await self.source.ai_generate(entity, prompt)
        except Exception as err:  # the report must not depend on an AI service
            _LOGGER.warning("AI summary failed: %s", err)
            return
        if isinstance(text, str) and text.strip():
            doc["story"] = {"text": text.strip(), "entity": entity}

    async def backfill(self, months: int, overwrite: bool = False) -> None:
        first = await first_month(self.source)
        if first is None:
            _LOGGER.info("Backfill skipped: no grid statistics in the energy dashboard")
            return
        y, m = prev_month(dt_util.now().date())
        done = 0
        for _ in range(months):
            ym = f"{y:04d}-{m:02d}"
            if (y, m) < first:
                break
            if overwrite or ym not in self.store.docs:
                try:
                    await self.generate(y, m)
                    done += 1
                except Exception:  # keep going; one bad month must not stop the rest
                    _LOGGER.exception("Could not generate %s", ym)
                await asyncio.sleep(1)  # be gentle on the recorder and Open-Meteo
            m -= 1
            if m == 0:
                y, m = y - 1, 12
        _LOGGER.info("Backfill finished: %s month(s) generated", done)

    def start_backfill(self, months: int, initial: bool = False, overwrite: bool = False) -> None:
        if self.backfill_task and not self.backfill_task.done():
            raise HomeAssistantError("A backfill is already running")

        async def run() -> None:
            await self.backfill(months, overwrite)
            if initial:
                self.hass.config_entries.async_update_entry(self.entry, data={**self.entry.data, "backfilled": True})

        self.backfill_task = self.entry.async_create_background_task(self.hass, run(), "home_in_review_backfill")

    async def scheduled(self, now: dt.datetime) -> None:
        if now.day != int(self.options.get(CONF_REPORT_DAY, DEFAULT_REPORT_DAY)):
            return
        y, m = prev_month(now.date())
        try:
            doc = await self.generate(y, m)
        except Exception:
            _LOGGER.exception("Monthly report for %04d-%02d failed", y, m)
            return
        await self.notify(doc)
        start = int(self.options.get(CONF_YEAR_START, 1))
        if m % 12 + 1 == start:  # the last month of the report year: the year review is complete
            await self.notify(doc, year_key=render.year_key(f"{y:04d}-{m:02d}", start))

    async def catch_up(self) -> None:
        """After a restart past the report moment, make last month's report if it is missing."""
        now = dt_util.now()
        if now.day < int(self.options.get(CONF_REPORT_DAY, DEFAULT_REPORT_DAY)):
            return
        y, m = prev_month(now.date())
        if f"{y:04d}-{m:02d}" not in self.store.docs and await first_month(self.source):
            doc = await self.generate(y, m)
            await self.notify(doc)

    async def notify(self, doc: dict, year_key: str | None = None) -> None:
        services = self.options.get(CONF_NOTIFY) or []
        if not services:
            return
        L = Lang(self.hass.config.language, doc["units"].get("currency", "EUR"))
        p = doc["period"]
        ym = f'{p["year"]:04d}-{p["month"]:02d}'
        title = f'{L("title")}: {L.month(p["month"])} {p["year"]}'
        e = doc.get("energy") or {}
        parts = []
        if year_key:
            ms = [m for m in render.year_months(year_key) if m in self.store.docs]
            ds = [self.store.docs[m].get("energy") or {} for m in ms]
            title = f'{L("title")}: {L("year_title")} {render.year_label(year_key)}'
            parts.append(f'{L.num(sum(x.get("consumption") or 0 for x in ds))} kWh {L("used")}')
            if all(x.get("total_cost") is not None for x in ds):
                parts.append(f'{L.money(sum(x["total_cost"] for x in ds))} {L("net_cost")}')
            ym = f"year-{year_key}"
            e = {}
        if e.get("consumption") is not None:
            parts.append(f'{L.num(e["consumption"])} kWh {L("used")}')
        if e.get("total_cost") is not None:
            parts.append(f'{L.money(e["total_cost"])} {L("net_cost")}')
        if not year_key and (doc.get("weather") or {}).get("temp") is not None:
            parts.append(f'{L.num(doc["weather"]["temp"], 1)}{doc["units"]["temperature"]} {L("outside")}')
        url = f"/{PANEL_URL}/{ym}"
        for svc in services:
            domain, _, name = svc.partition(".")
            if not name:
                domain, name = "notify", svc
            try:
                await self.hass.services.async_call(domain, name, {
                    "title": title, "message": " · ".join(parts),
                    "data": {"url": url, "clickAction": url}}, blocking=False)
            except Exception:  # a removed phone must not break the report
                _LOGGER.warning("Notification via %s failed", svc, exc_info=True)


# ============================================================================ setup
async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    hass.http.register_view(ReportView())
    await hass.http.async_register_static_paths(
        [StaticPathConfig(STATIC_URL, str(FRONTEND), True)])

    async def svc_generate(call: ServiceCall) -> dict:
        rt = _runtime(hass)
        ym = call.data.get("month")
        if ym:
            if not YM.match(ym):
                raise HomeAssistantError("month must look like 2026-10")
            y, m = map(int, ym.split("-"))
        else:
            y, m = prev_month(dt_util.now().date())
        doc = await rt.generate(y, m)
        if call.data.get("notify"):
            await rt.notify(doc)
        return {"month": f"{y:04d}-{m:02d}", "sections": doc.get("sections", [])}

    async def svc_backfill(call: ServiceCall) -> None:
        _runtime(hass).start_backfill(int(call.data.get("months", DEFAULT_BACKFILL_MONTHS)),
                                      overwrite=bool(call.data.get("overwrite")))

    hass.services.async_register(DOMAIN, "generate", svc_generate, vol.Schema({
        vol.Optional("month"): cv.string, vol.Optional("notify", default=False): cv.boolean}),
        supports_response=SupportsResponse.OPTIONAL)
    hass.services.async_register(DOMAIN, "backfill", svc_backfill, vol.Schema({
        vol.Optional("months", default=DEFAULT_BACKFILL_MONTHS): vol.All(vol.Coerce(int), vol.Range(1, 120)),
        vol.Optional("overwrite", default=False): cv.boolean}))
    return True


def _runtime(hass: HomeAssistant) -> HomeInReview:
    entries = hass.config_entries.async_loaded_entries(DOMAIN)
    if not entries:
        raise HomeAssistantError("Home in Review is not set up")
    return entries[0].runtime_data


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    rt = HomeInReview(hass, entry)
    await rt.store.async_load()
    entry.runtime_data = rt

    t = dt.time.fromisoformat(str(rt.options.get(CONF_REPORT_TIME, DEFAULT_REPORT_TIME)))
    entry.async_on_unload(async_track_time_change(hass, rt.scheduled, hour=t.hour, minute=t.minute, second=t.second))
    entry.async_on_unload(entry.add_update_listener(_reload))

    if PANEL_URL not in hass.data.get(frontend.DATA_PANELS, {}):
        await panel_custom.async_register_panel(
            hass, frontend_url_path=PANEL_URL, webcomponent_name="home-in-review-panel",
            sidebar_title="Home in Review", sidebar_icon="mdi:home-analytics",
            module_url=f"{STATIC_URL}/panel.js?v={await hass.async_add_executor_job(_version)}", require_admin=False, config={})

    @callback
    def started(_=None) -> None:
        # The initial backfill is marked done only when it finished, so a restart halfway resumes it
        # (months that already exist are skipped).
        if not entry.data.get("backfilled") and entry.data.get(CONF_BACKFILL_MONTHS, DEFAULT_BACKFILL_MONTHS):
            rt.start_backfill(int(entry.data.get(CONF_BACKFILL_MONTHS, DEFAULT_BACKFILL_MONTHS)), initial=True)
        else:
            entry.async_create_background_task(hass, rt.catch_up(), "home_in_review_catch_up")

    if hass.is_running:
        started()
    else:
        entry.async_on_unload(hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STARTED, started))
    return True


async def _reload(hass: HomeAssistant, entry: ConfigEntry) -> None:
    # Only option changes need a reload; entry.data also changes when the initial backfill is marked done,
    # and reloading then would cancel running work.
    rt: HomeInReview = entry.runtime_data
    if dict(entry.options) != rt.loaded_options:
        await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    rt: HomeInReview = entry.runtime_data
    if rt.backfill_task and not rt.backfill_task.done():
        rt.backfill_task.cancel()
    return True


async def async_remove_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    frontend.async_remove_panel(hass, PANEL_URL)


def _version() -> str:
    try:
        return json.loads((Path(__file__).parent / "manifest.json").read_text())["version"]
    except (OSError, ValueError, KeyError):
        return "0"


# ============================================================================ HTTP
class ReportView(HomeAssistantView):
    """GET /api/home_in_review/report/<YYYY-MM|index> -> HTML. Requires a logged-in user (or a signed path)."""

    url = URL_BASE + "/report/{name}"
    name = "api:home_in_review:report"
    requires_auth = True

    async def get(self, request: web.Request, name: str) -> web.Response:
        hass: HomeAssistant = request.app["hass"]
        entries = hass.config_entries.async_loaded_entries(DOMAIN)
        if not entries:
            return web.Response(status=404)
        rt: HomeInReview = entries[0].runtime_data
        docs = rt.store.docs
        lang = request.query.get("lang") or hass.config.language
        home = hass.config.location_name
        start = int(rt.options.get(CONF_YEAR_START, 1))
        if name == "index":
            html = render.render_index(docs, lang, home, hass.config.currency, start)
        elif name.startswith("year-") and YM.match(name[5:]):
            try:
                html = await hass.async_add_executor_job(render.render_year, name[5:], docs, lang, home, start)
            except KeyError:
                return web.Response(status=404)
        elif YM.match(name) and name in docs:
            html = await hass.async_add_executor_job(render.render_month, name, docs, lang, home, start)
        else:
            return web.Response(status=404)
        return web.Response(text=html, content_type="text/html", charset="utf-8",
                            headers={"Cache-Control": "no-store", "X-Content-Type-Options": "nosniff"})
