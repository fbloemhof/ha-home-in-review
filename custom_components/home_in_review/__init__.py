"""Home in Review: a monthly report of your home, built from data Home Assistant already has.

- Collects a month from the energy dashboard, Open-Meteo weather and indoor climate sensors (collector.py).
- Stores one JSON document per month in <config>/home_in_review/.
- Serves the reports as HTML, rendered on request (render.py), only to logged-in users.
- Adds a sidebar panel, a monthly schedule with optional notifications, and generate/backfill actions.
"""
from __future__ import annotations

import asyncio
import datetime as dt
import hashlib
import json
import logging
from pathlib import Path

import voluptuous as vol
from homeassistant.components import frontend, panel_custom
from homeassistant.components.http import StaticPathConfig
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall, SupportsResponse, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.event import async_track_time_change
from homeassistant.helpers.start import async_at_started
from homeassistant.util import dt as dt_util

from . import render, story
from .collector import Collector, first_month
from .const import (
    CONF_ADMIN_ONLY,
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
)
from .hass_source import HassSource
from .i18n import Lang
from .options import sanitize
from .store import ReportStore
from .views import YM, ReportView

# Bump when the collector's output changes, so existing reports are re-made after an update.
COLLECTOR_VERSION = 4
PRESENTATION_OPTIONS = {"notify_services", "report_day", "report_time", "default_theme", "admin_only",
                        "year_start_month", "backfill_months", "backfilled"}

_LOGGER = logging.getLogger(__name__)
CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)
FRONTEND = Path(__file__).parent / "frontend"


def prev_month(today: dt.date) -> tuple[int, int]:
    first = today.replace(day=1) - dt.timedelta(days=1)
    return first.year, first.month


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
        """Entry data and options, validated (see options.py)."""
        return sanitize({**self.entry.data, **self.entry.options})

    def fingerprint(self) -> str:
        """What a report depends on besides the data: the collector version and the options that change figures.
        Presentation-only options (notifications, schedule, theme, access, year start) are left out. AI settings count:
        unchanged summaries are reused (see _story), so this costs no extra AI calls."""
        relevant = {k: v for k, v in sorted(self.options.items()) if k not in PRESENTATION_OPTIONS}
        raw = json.dumps({"collector": COLLECTOR_VERSION, "options": relevant}, sort_keys=True, default=str)
        return hashlib.sha256(raw.encode()).hexdigest()[:16]

    def stale_months(self) -> list[str]:
        fp = self.fingerprint()
        return sorted((ym for ym, d in self.store.docs.items() if (d.get("meta") or {}).get("fingerprint") != fp),
                      reverse=True)

    async def generate(self, year: int, month: int) -> dict:
        ym = f"{year:04d}-{month:02d}"
        async with self.lock:
            previous = self.store.docs.get(ym)
            doc = await Collector(self.source, self.options, self.store.cache).collect(year, month)
            doc["meta"] = {"fingerprint": self.fingerprint(), "collector": COLLECTOR_VERSION}
            await self._story(ym, doc, previous)
            await self.store.async_save(ym, doc)
            return doc

    async def refresh(self, months: list[str]) -> None:
        """Re-make reports made by an older version or with other settings, newest first, one at a time."""
        _LOGGER.info("Updating %s report(s) for a new version or changed settings", len(months))
        for ym in months:
            try:
                await self.generate(int(ym[:4]), int(ym[5:]))
            except Exception:  # keep going; one bad month must not stop the rest
                _LOGGER.exception("Could not update %s", ym)
            await asyncio.sleep(1)

    async def _story(self, ym: str, doc: dict, previous: dict | None = None) -> None:
        """Optional AI-written summary through the user's own AI Task entity. When the figures it is written from
        are unchanged (same prompt), the earlier text is kept instead of asking the AI again."""
        entity = self.options.get(CONF_AI_TASK)
        if not entity:
            return
        docs = {**self.store.docs, ym: doc}
        prompt = story.instructions(ym, docs, self.hass.config.language, self.options.get(CONF_AI_INSTRUCTIONS))
        digest = hashlib.sha256(f"{entity}\n{prompt}".encode()).hexdigest()[:16]
        old = (previous or {}).get("story") or {}
        if old.get("text") and old.get("hash") == digest:
            doc["story"] = old
            return
        try:
            text = await self.source.ai_generate(entity, prompt)
        except HomeAssistantError as err:  # the AI service refused or is unavailable
            _LOGGER.warning("AI summary for %s skipped: %s", ym, err)
            return
        except Exception:  # anything else is a bug; log it, but the report must not depend on an AI service
            _LOGGER.exception("AI summary for %s failed", ym)
            return
        if isinstance(text, str) and text.strip():
            doc["story"] = {"text": text.strip(), "entity": entity, "hash": digest}

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
        rt = _runtime(hass)
        months = call.data.get("months")
        if months is None:  # default: back to the start of last year's report year, so both year reviews are complete
            start = int(rt.options.get(CONF_YEAR_START, 1))
            months = 12 + (dt_util.now().month - start) % 12
        rt.start_backfill(int(months), overwrite=bool(call.data.get("overwrite")))

    hass.services.async_register(DOMAIN, "generate", svc_generate, vol.Schema({
        vol.Optional("month"): cv.string, vol.Optional("notify", default=False): cv.boolean}),
        supports_response=SupportsResponse.OPTIONAL)
    hass.services.async_register(DOMAIN, "backfill", svc_backfill, vol.Schema({
        vol.Optional("months"): vol.All(vol.Coerce(int), vol.Range(1, 120)),
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

    # The panel is registered per entry so a change of the "administrators only" option takes effect on reload.
    if PANEL_URL in hass.data.get(frontend.DATA_PANELS, {}):
        frontend.async_remove_panel(hass, PANEL_URL)
    await panel_custom.async_register_panel(
        hass, frontend_url_path=PANEL_URL, webcomponent_name="home-in-review-panel",
        sidebar_title="Home in Review", sidebar_icon="mdi:home-analytics",
        module_url=f"{STATIC_URL}/panel.js?v={await hass.async_add_executor_job(_version)}",
        require_admin=bool(rt.options.get(CONF_ADMIN_ONLY)), config={})

    @callback
    def started(_hass: HomeAssistant | None = None) -> None:
        # The initial backfill is marked done only when it finished, so a restart halfway resumes it
        # (months that already exist are skipped).
        if not entry.data.get("backfilled") and entry.data.get(CONF_BACKFILL_MONTHS, DEFAULT_BACKFILL_MONTHS):
            rt.start_backfill(int(entry.data.get(CONF_BACKFILL_MONTHS, DEFAULT_BACKFILL_MONTHS)), initial=True)
        else:
            entry.async_create_background_task(hass, rt.catch_up(), "home_in_review_catch_up")
        # After an update or a change of settings: bring the existing reports up to date in the background.
        if stale := rt.stale_months():
            entry.async_create_background_task(hass, rt.refresh(stale), "home_in_review_refresh")

    # Runs now when Home Assistant is already up, otherwise once it has started; safe to cancel on unload.
    entry.async_on_unload(async_at_started(hass, started))
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
    if PANEL_URL in hass.data.get(frontend.DATA_PANELS, {}):
        frontend.async_remove_panel(hass, PANEL_URL)
    return True


def _version() -> str:
    try:
        return json.loads((Path(__file__).parent / "manifest.json").read_text())["version"]
    except (OSError, ValueError, KeyError):
        return "0"
