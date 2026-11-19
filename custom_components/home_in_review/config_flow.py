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
from homeassistant.data_entry_flow import section
from homeassistant.helpers import area_registry as ar
from homeassistant.helpers import floor_registry as fr
from homeassistant.helpers import selector

from .collector import is_outdoor_name
from .const import (
    CONF_AI_INSTRUCTIONS,
    CONF_AI_TASK,
    CONF_BACKFILL_MONTHS,
    CONF_CAR_CHARGERS,
    CONF_CAR_ODOMETERS,
    CONF_EVCC_URL,
    CONF_EXCLUDED_AREAS,
    CONF_FIXED_DAILY,
    CONF_FIXED_MONTHLY,
    CONF_HP_DEVICES,
    CONF_HP_HEAT,
    CONF_MAX_HOURLY_KWH,
    CONF_NOTIFY,
    CONF_OUTDOOR_SENSOR,
    CONF_RAIN_SENSOR,
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


def _as_list(value: Any) -> list[str] | None:
    if not value:
        return None
    return [value] if isinstance(value, str) else list(value)


def _suggest(value: Any) -> dict:
    return {"suggested_value": value} if value not in (None, "") else {}


# Settings form: one form with collapsible sections; key -> fields in that section.
SECTIONS = {
    "general": [CONF_NOTIFY, CONF_REPORT_DAY, CONF_REPORT_TIME, CONF_YEAR_START],
    "energy": [CONF_FIXED_DAILY, CONF_FIXED_MONTHLY, CONF_MAX_HOURLY_KWH, CONF_HP_DEVICES, CONF_HP_HEAT],
    "climate": [CONF_EXCLUDED_AREAS, CONF_OUTDOOR_SENSOR, CONF_RAIN_SENSOR, CONF_USE_OPEN_METEO],
    "car": [CONF_CAR_ODOMETERS, CONF_CAR_CHARGERS, CONF_EVCC_URL, CONF_TM_URL, CONF_TM_TOKEN, CONF_TM_HOME],
    "ai": [CONF_AI_TASK, CONF_AI_INSTRUCTIONS],
}


class HomeInReviewOptionsFlow(OptionsFlow):
    """A short menu: the settings (one form with sections), and adding or removing own figures.

    Every path ends by saving, because Home Assistant forms have no way back to a menu.
    """

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        menu = ["settings", "tile_add"]
        if self.config_entry.options.get(CONF_TILES):
            menu.append("tile_remove")
        return self.async_show_menu(step_id="init", menu_options=menu)

    # ------------------------------------------------------------------ settings
    async def async_step_settings(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        o = dict(self.config_entry.options)
        if user_input is not None:
            flat: dict[str, Any] = {}
            for part in user_input.values():
                if isinstance(part, dict):
                    flat.update(part)
            for keys in SECTIONS.values():
                for k in keys:
                    if k in flat and flat[k] not in (None, "", []):
                        o[k] = flat[k]
                    else:
                        o.pop(k, None)
            # An emptied area list means "exclude nothing" ([]); a missing key would bring back the automatic
            # outdoor exclusion.
            o[CONF_EXCLUDED_AREAS] = flat.get(CONF_EXCLUDED_AREAS) or []
            o[CONF_USE_OPEN_METEO] = bool(flat.get(CONF_USE_OPEN_METEO, True))
            o[CONF_YEAR_START] = int(flat.get(CONF_YEAR_START, 1))
            return self.async_create_entry(data=o)

        notify = sorted(f"notify.{name}" for name in self.hass.services.async_services_for_domain("notify")
                        if name not in ("send_message", "persistent_notification"))
        excluded = o.get(CONF_EXCLUDED_AREAS)
        if excluded is None:
            excluded = self._suggested_excluded_areas()
        general = vol.Schema({
            vol.Optional(CONF_NOTIFY, default=o.get(CONF_NOTIFY, [])): selector.SelectSelector(
                selector.SelectSelectorConfig(options=notify, multiple=True, custom_value=True)),
            vol.Required(CONF_REPORT_DAY, default=o.get(CONF_REPORT_DAY, DEFAULT_REPORT_DAY)): selector.NumberSelector(
                selector.NumberSelectorConfig(min=1, max=28, step=1, mode=BOX)),
            vol.Required(CONF_REPORT_TIME, default=o.get(CONF_REPORT_TIME, DEFAULT_REPORT_TIME)): selector.TimeSelector(),
            vol.Required(CONF_YEAR_START, default=str(o.get(CONF_YEAR_START, 1))): selector.SelectSelector(
                selector.SelectSelectorConfig(options=[str(i) for i in range(1, 13)], translation_key="month",
                                              mode=selector.SelectSelectorMode.DROPDOWN)),
        })
        energy = vol.Schema({
            vol.Optional(CONF_FIXED_DAILY, description=_suggest(o.get(CONF_FIXED_DAILY))): selector.NumberSelector(
                selector.NumberSelectorConfig(min=0, max=100, step="any", mode=BOX)),
            vol.Optional(CONF_FIXED_MONTHLY, description=_suggest(o.get(CONF_FIXED_MONTHLY))): selector.NumberSelector(
                selector.NumberSelectorConfig(min=-1000, max=10000, step="any", mode=BOX)),
            vol.Required(CONF_MAX_HOURLY_KWH, default=o.get(CONF_MAX_HOURLY_KWH, DEFAULT_MAX_HOURLY_KWH)): selector.NumberSelector(
                selector.NumberSelectorConfig(min=1, max=1000, step=1, mode=BOX, unit_of_measurement="kWh")),
            vol.Optional(CONF_HP_DEVICES, description=_suggest(_as_list(o.get(CONF_HP_DEVICES)))): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="sensor", device_class="energy", multiple=True)),
            vol.Optional(CONF_HP_HEAT, description=_suggest(_as_list(o.get(CONF_HP_HEAT)))): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="sensor", device_class="energy", multiple=True)),
        })
        climate = vol.Schema({
            vol.Optional(CONF_EXCLUDED_AREAS, description=_suggest(excluded)): selector.AreaSelector(
                selector.AreaSelectorConfig(multiple=True)),
            vol.Optional(CONF_OUTDOOR_SENSOR, description=_suggest(o.get(CONF_OUTDOOR_SENSOR))): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="sensor", device_class="temperature")),
            vol.Optional(CONF_RAIN_SENSOR, description=_suggest(o.get(CONF_RAIN_SENSOR))): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="sensor", device_class="precipitation")),
            vol.Required(CONF_USE_OPEN_METEO, default=o.get(CONF_USE_OPEN_METEO, True)): selector.BooleanSelector(),
        })
        car = vol.Schema({
            vol.Optional(CONF_CAR_ODOMETERS, description=_suggest(o.get(CONF_CAR_ODOMETERS))): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="sensor", device_class="distance", multiple=True)),
            vol.Optional(CONF_CAR_CHARGERS, description=_suggest(o.get(CONF_CAR_CHARGERS))): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="sensor", device_class="energy", multiple=True)),
            vol.Optional(CONF_EVCC_URL, description=_suggest(o.get(CONF_EVCC_URL))): selector.TextSelector(
                selector.TextSelectorConfig(type=selector.TextSelectorType.URL)),
            vol.Optional(CONF_TM_URL, description=_suggest(o.get(CONF_TM_URL))): selector.TextSelector(
                selector.TextSelectorConfig(type=selector.TextSelectorType.URL)),
            vol.Optional(CONF_TM_TOKEN, description=_suggest(o.get(CONF_TM_TOKEN))): selector.TextSelector(
                selector.TextSelectorConfig(type=selector.TextSelectorType.PASSWORD)),
            vol.Optional(CONF_TM_HOME, description=_suggest(o.get(CONF_TM_HOME))): selector.TextSelector(),
        })
        ai = vol.Schema({
            vol.Optional(CONF_AI_TASK, description=_suggest(o.get(CONF_AI_TASK))): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="ai_task")),
            vol.Optional(CONF_AI_INSTRUCTIONS, description=_suggest(o.get(CONF_AI_INSTRUCTIONS))): selector.TextSelector(
                selector.TextSelectorConfig(multiline=True)),
        })
        return self.async_show_form(step_id="settings", data_schema=vol.Schema({
            vol.Required("general"): section(general, {"collapsed": False}),
            vol.Required("energy"): section(energy, {"collapsed": True}),
            vol.Required("climate"): section(climate, {"collapsed": True}),
            vol.Required("car"): section(car, {"collapsed": True}),
            vol.Required("ai"): section(ai, {"collapsed": True}),
        }))

    def _suggested_excluded_areas(self) -> list[str]:
        floors = fr.async_get(self.hass)
        out = []
        for area in ar.async_get(self.hass).async_list_areas():
            floor = floors.async_get_floor(area.floor_id) if area.floor_id else None
            if is_outdoor_name(area.name) or (floor and is_outdoor_name(floor.name)):
                out.append(area.id)
        return out

    # ------------------------------------------------------------------ custom tiles
    async def async_step_tile_add(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        # The statistic field is optional in the schema because the frontend can't build initial data for a
        # required statistic selector (the form stays empty); it is checked here instead.
        errors: dict[str, str] = {}
        if user_input is not None and not user_input.get("statistic"):
            errors["statistic"] = "statistic_required"
        elif user_input is not None:
            tile = {"name": user_input["name"], "statistic": user_input["statistic"], "type": user_input["type"],
                    "unit": user_input.get("unit") or "", "decimals": int(user_input.get("decimals", 0))}
            if user_input.get("threshold") is not None:
                tile["threshold"] = float(user_input["threshold"])
            if user_input.get("run_hours"):
                tile["run_hours"] = float(user_input["run_hours"])
            o = dict(self.config_entry.options)
            o[CONF_TILES] = [*o.get(CONF_TILES, []), tile]
            return self.async_create_entry(data=o)
        return self.async_show_form(step_id="tile_add", data_schema=vol.Schema({
            vol.Required("name", default=(user_input or {}).get("name", "")): selector.TextSelector(),
            vol.Optional("statistic", description=_suggest((user_input or {}).get("statistic"))): selector.StatisticSelector(
                selector.StatisticSelectorConfig()),
            vol.Required("type", default="sum"): selector.SelectSelector(
                selector.SelectSelectorConfig(options=list(TILE_TYPES), translation_key="tile_type")),
            vol.Optional("threshold"): selector.NumberSelector(selector.NumberSelectorConfig(step="any", mode=BOX)),
            vol.Optional("run_hours"): selector.NumberSelector(
                selector.NumberSelectorConfig(min=0.5, max=24, step=0.5, mode=BOX, unit_of_measurement="h")),
            vol.Optional("unit"): selector.TextSelector(),
            vol.Optional("decimals", default=0): selector.NumberSelector(
                selector.NumberSelectorConfig(min=0, max=3, step=1, mode=BOX)),
        }), errors=errors)

    async def async_step_tile_remove(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        tiles = self.config_entry.options.get(CONF_TILES, [])
        if user_input is not None:
            drop = {int(i) for i in user_input.get("tiles", [])}
            o = dict(self.config_entry.options)
            o[CONF_TILES] = [t for i, t in enumerate(tiles) if i not in drop]
            return self.async_create_entry(data=o)
        options = [selector.SelectOptionDict(value=str(i), label=f'{t["name"]} ({t["statistic"]}, {t["type"]})')
                   for i, t in enumerate(tiles)]
        return self.async_show_form(step_id="tile_remove", data_schema=vol.Schema({
            vol.Optional("tiles", default=[]): selector.SelectSelector(
                selector.SelectSelectorConfig(options=options, multiple=True, mode=selector.SelectSelectorMode.LIST)),
        }))
