"""Config and options flow for Home in Review.

Options are grouped in a menu; every group edits a working copy that is stored when the user picks "Save".
"""
from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.core import callback
from homeassistant.helpers import area_registry as ar
from homeassistant.helpers import floor_registry as fr
from homeassistant.helpers import selector

from .collector import is_outdoor_name, parse_energy_prefs
from .const import (
    CONF_AI_INSTRUCTIONS,
    CONF_AI_TASK,
    CONF_BACKFILL_MONTHS,
    CONF_EXCLUDED_AREAS,
    CONF_FIXED_DAILY,
    CONF_FIXED_MONTHLY,
    CONF_HP_DEVICES,
    CONF_HP_HEAT,
    CONF_MAX_HOURLY_KWH,
    CONF_NOTIFY,
    CONF_OUTDOOR_SENSOR,
    CONF_REPORT_DAY,
    CONF_REPORT_TIME,
    CONF_TILES,
    CONF_TM_HOME,
    CONF_TM_TOKEN,
    CONF_TM_URL,
    CONF_USE_OPEN_METEO,
    CONF_YEAR_START,
    DEFAULT_BACKFILL_MONTHS,
    DEFAULT_MAX_HOURLY_KWH,
    DEFAULT_REPORT_DAY,
    DEFAULT_REPORT_TIME,
    DOMAIN,
    NAME,
)
from .extras import TILE_TYPES
from .hass_source import HassSource

BOX = selector.NumberSelectorMode.BOX


class HomeInReviewConfigFlow(ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        if self._async_current_entries():
            return self.async_abort(reason="single_instance_allowed")
        if user_input is not None:
            return self.async_create_entry(title=NAME, data={CONF_BACKFILL_MONTHS: int(user_input[CONF_BACKFILL_MONTHS])})
        return self.async_show_form(step_id="user", data_schema=vol.Schema({
            vol.Required(CONF_BACKFILL_MONTHS, default=DEFAULT_BACKFILL_MONTHS): selector.NumberSelector(
                selector.NumberSelectorConfig(min=0, max=60, step=1, mode=BOX)),
        }))

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        return HomeInReviewOptionsFlow()


def _suggest(value: Any) -> dict:
    return {"suggested_value": value} if value not in (None, "") else {}


class HomeInReviewOptionsFlow(OptionsFlow):
    def __init__(self) -> None:
        self.opts: dict[str, Any] | None = None

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        if self.opts is None:
            self.opts = dict(self.config_entry.options)
        return self.async_show_menu(step_id="init", menu_options=[
            "general", "energy", "climate", "car", "ai", "tile_add", "tile_remove", "save"])

    async def async_step_save(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        return self.async_create_entry(data=self.opts)

    def _merge(self, user_input: dict[str, Any], keys: list[str]) -> None:
        """Store a group: given values replace the old ones, emptied optional fields are removed."""
        for k in keys:
            if k in user_input and user_input[k] not in (None, ""):
                self.opts[k] = user_input[k]
            else:
                self.opts.pop(k, None)

    # ------------------------------------------------------------------ general
    async def async_step_general(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        o = self.opts
        if user_input is not None:
            self._merge(user_input, [CONF_NOTIFY, CONF_REPORT_DAY, CONF_REPORT_TIME])
            self.opts[CONF_YEAR_START] = int(user_input.get(CONF_YEAR_START, 1))
            return await self.async_step_init()
        notify = sorted(f"notify.{name}" for name in self.hass.services.async_services_for_domain("notify")
                        if name not in ("send_message", "persistent_notification"))
        return self.async_show_form(step_id="general", data_schema=vol.Schema({
            vol.Optional(CONF_NOTIFY, default=o.get(CONF_NOTIFY, [])): selector.SelectSelector(
                selector.SelectSelectorConfig(options=notify, multiple=True, custom_value=True)),
            vol.Required(CONF_REPORT_DAY, default=o.get(CONF_REPORT_DAY, DEFAULT_REPORT_DAY)): selector.NumberSelector(
                selector.NumberSelectorConfig(min=1, max=28, step=1, mode=BOX)),
            vol.Required(CONF_REPORT_TIME, default=o.get(CONF_REPORT_TIME, DEFAULT_REPORT_TIME)): selector.TimeSelector(),
            vol.Required(CONF_YEAR_START, default=str(o.get(CONF_YEAR_START, 1))): selector.SelectSelector(
                selector.SelectSelectorConfig(options=[str(i) for i in range(1, 13)], translation_key="month",
                                              mode=selector.SelectSelectorMode.DROPDOWN)),
        }))

    # ------------------------------------------------------------------ energy
    async def async_step_energy(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        o = self.opts
        if user_input is not None:
            self._merge(user_input, [CONF_FIXED_DAILY, CONF_FIXED_MONTHLY, CONF_MAX_HOURLY_KWH, CONF_HP_DEVICES, CONF_HP_HEAT])
            return await self.async_step_init()
        prefs = parse_energy_prefs(await HassSource(self.hass).energy_prefs())
        devices = [selector.SelectOptionDict(value=d["stat"], label=d.get("name") or d["stat"]) for d in prefs["devices"]]
        return self.async_show_form(step_id="energy", data_schema=vol.Schema({
            vol.Optional(CONF_FIXED_DAILY, description=_suggest(o.get(CONF_FIXED_DAILY))): selector.NumberSelector(
                selector.NumberSelectorConfig(min=0, max=100, step="any", mode=BOX)),
            vol.Optional(CONF_FIXED_MONTHLY, description=_suggest(o.get(CONF_FIXED_MONTHLY))): selector.NumberSelector(
                selector.NumberSelectorConfig(min=-1000, max=10000, step="any", mode=BOX)),
            vol.Required(CONF_MAX_HOURLY_KWH, default=o.get(CONF_MAX_HOURLY_KWH, DEFAULT_MAX_HOURLY_KWH)): selector.NumberSelector(
                selector.NumberSelectorConfig(min=1, max=1000, step=1, mode=BOX, unit_of_measurement="kWh")),
            vol.Optional(CONF_HP_DEVICES, default=o.get(CONF_HP_DEVICES, [])): selector.SelectSelector(
                selector.SelectSelectorConfig(options=devices, multiple=True)),
            vol.Optional(CONF_HP_HEAT, description=_suggest(o.get(CONF_HP_HEAT))): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="sensor", device_class="energy")),
        }))

    # ------------------------------------------------------------------ climate & weather
    async def async_step_climate(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        o = self.opts
        if user_input is not None:
            # An emptied area list is stored as [] ("exclude nothing"); a missing key would bring back the
            # automatic outdoor exclusion.
            self.opts[CONF_EXCLUDED_AREAS] = user_input.get(CONF_EXCLUDED_AREAS) or []
            self._merge(user_input, [CONF_OUTDOOR_SENSOR])
            self.opts[CONF_USE_OPEN_METEO] = bool(user_input.get(CONF_USE_OPEN_METEO, True))
            return await self.async_step_init()
        excluded = o.get(CONF_EXCLUDED_AREAS)
        if excluded is None:
            excluded = self._suggested_excluded_areas()
        return self.async_show_form(step_id="climate", data_schema=vol.Schema({
            vol.Optional(CONF_EXCLUDED_AREAS, description=_suggest(excluded)): selector.AreaSelector(
                selector.AreaSelectorConfig(multiple=True)),
            vol.Optional(CONF_OUTDOOR_SENSOR, description=_suggest(o.get(CONF_OUTDOOR_SENSOR))): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="sensor", device_class="temperature")),
            vol.Required(CONF_USE_OPEN_METEO, default=o.get(CONF_USE_OPEN_METEO, True)): selector.BooleanSelector(),
        }))

    def _suggested_excluded_areas(self) -> list[str]:
        floors = fr.async_get(self.hass)
        out = []
        for area in ar.async_get(self.hass).async_list_areas():
            floor = floors.async_get_floor(area.floor_id) if area.floor_id else None
            if is_outdoor_name(area.name) or (floor and is_outdoor_name(floor.name)):
                out.append(area.id)
        return out

    # ------------------------------------------------------------------ car
    async def async_step_car(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        o = self.opts
        if user_input is not None:
            self._merge(user_input, [CONF_TM_URL, CONF_TM_TOKEN, CONF_TM_HOME])
            return await self.async_step_init()
        return self.async_show_form(step_id="car", data_schema=vol.Schema({
            vol.Optional(CONF_TM_URL, description=_suggest(o.get(CONF_TM_URL))): selector.TextSelector(
                selector.TextSelectorConfig(type=selector.TextSelectorType.URL)),
            vol.Optional(CONF_TM_TOKEN, description=_suggest(o.get(CONF_TM_TOKEN))): selector.TextSelector(
                selector.TextSelectorConfig(type=selector.TextSelectorType.PASSWORD)),
            vol.Optional(CONF_TM_HOME, description=_suggest(o.get(CONF_TM_HOME))): selector.TextSelector(),
        }))

    # ------------------------------------------------------------------ AI summary
    async def async_step_ai(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        o = self.opts
        if user_input is not None:
            self._merge(user_input, [CONF_AI_TASK, CONF_AI_INSTRUCTIONS])
            return await self.async_step_init()
        return self.async_show_form(step_id="ai", data_schema=vol.Schema({
            vol.Optional(CONF_AI_TASK, description=_suggest(o.get(CONF_AI_TASK))): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="ai_task")),
            vol.Optional(CONF_AI_INSTRUCTIONS, description=_suggest(o.get(CONF_AI_INSTRUCTIONS))): selector.TextSelector(
                selector.TextSelectorConfig(multiline=True)),
        }))

    # ------------------------------------------------------------------ custom tiles
    async def async_step_tile_add(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        if user_input is not None:
            tile = {"name": user_input["name"], "statistic": user_input["statistic"], "type": user_input["type"],
                    "unit": user_input.get("unit") or "", "decimals": int(user_input.get("decimals", 0))}
            if user_input.get("threshold") is not None:
                tile["threshold"] = float(user_input["threshold"])
            self.opts[CONF_TILES] = [*self.opts.get(CONF_TILES, []), tile]
            return await self.async_step_init()
        return self.async_show_form(step_id="tile_add", data_schema=vol.Schema({
            vol.Required("name"): selector.TextSelector(),
            vol.Required("statistic"): selector.StatisticSelector(selector.StatisticSelectorConfig()),
            vol.Required("type", default="sum"): selector.SelectSelector(
                selector.SelectSelectorConfig(options=list(TILE_TYPES), translation_key="tile_type")),
            vol.Optional("threshold"): selector.NumberSelector(selector.NumberSelectorConfig(step="any", mode=BOX)),
            vol.Optional("unit"): selector.TextSelector(),
            vol.Optional("decimals", default=0): selector.NumberSelector(
                selector.NumberSelectorConfig(min=0, max=3, step=1, mode=BOX)),
        }))

    async def async_step_tile_remove(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        tiles = self.opts.get(CONF_TILES, [])
        if user_input is not None:
            drop = {int(i) for i in user_input.get("tiles", [])}
            self.opts[CONF_TILES] = [t for i, t in enumerate(tiles) if i not in drop]
            return await self.async_step_init()
        options = [selector.SelectOptionDict(value=str(i), label=f'{t["name"]} ({t["statistic"]}, {t["type"]})')
                   for i, t in enumerate(tiles)]
        return self.async_show_form(step_id="tile_remove", data_schema=vol.Schema({
            vol.Optional("tiles", default=[]): selector.SelectSelector(
                selector.SelectSelectorConfig(options=options, multiple=True)),
        }))
