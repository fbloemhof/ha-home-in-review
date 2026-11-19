"""Config and options flow for Home in Review."""
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

from .collector import is_outdoor_name
from .const import (
    CONF_BACKFILL_MONTHS,
    CONF_EXCLUDED_AREAS,
    CONF_FIXED_DAILY,
    CONF_FIXED_MONTHLY,
    CONF_MAX_HOURLY_KWH,
    CONF_NOTIFY,
    CONF_OUTDOOR_SENSOR,
    CONF_REPORT_DAY,
    CONF_REPORT_TIME,
    DEFAULT_BACKFILL_MONTHS,
    DEFAULT_MAX_HOURLY_KWH,
    DEFAULT_REPORT_DAY,
    DEFAULT_REPORT_TIME,
    DOMAIN,
    NAME,
)


class HomeInReviewConfigFlow(ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        if self._async_current_entries():
            return self.async_abort(reason="single_instance_allowed")
        if user_input is not None:
            return self.async_create_entry(title=NAME, data={CONF_BACKFILL_MONTHS: int(user_input[CONF_BACKFILL_MONTHS])})
        return self.async_show_form(step_id="user", data_schema=vol.Schema({
            vol.Required(CONF_BACKFILL_MONTHS, default=DEFAULT_BACKFILL_MONTHS): selector.NumberSelector(
                selector.NumberSelectorConfig(min=0, max=60, step=1, mode=selector.NumberSelectorMode.BOX)),
        }))

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        return HomeInReviewOptionsFlow()


class HomeInReviewOptionsFlow(OptionsFlow):
    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        if user_input is not None:
            return self.async_create_entry(data=user_input)
        o = self.config_entry.options
        notify = sorted(f"notify.{name}" for name in self.hass.services.async_services_for_domain("notify")
                        if name not in ("send_message", "persistent_notification"))
        excluded = o.get(CONF_EXCLUDED_AREAS)
        if excluded is None:
            excluded = self._suggested_excluded_areas()
        schema: dict[Any, Any] = {
            vol.Optional(CONF_NOTIFY, default=o.get(CONF_NOTIFY, [])): selector.SelectSelector(
                selector.SelectSelectorConfig(options=notify, multiple=True, custom_value=True)),
            vol.Required(CONF_REPORT_DAY, default=o.get(CONF_REPORT_DAY, DEFAULT_REPORT_DAY)): selector.NumberSelector(
                selector.NumberSelectorConfig(min=1, max=28, step=1, mode=selector.NumberSelectorMode.BOX)),
            vol.Required(CONF_REPORT_TIME, default=o.get(CONF_REPORT_TIME, DEFAULT_REPORT_TIME)): selector.TimeSelector(),
            vol.Optional(CONF_EXCLUDED_AREAS, default=excluded): selector.AreaSelector(
                selector.AreaSelectorConfig(multiple=True)),
            vol.Optional(CONF_OUTDOOR_SENSOR, description={"suggested_value": o.get(CONF_OUTDOOR_SENSOR)}): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="sensor", device_class="temperature")),
            vol.Optional(CONF_FIXED_DAILY, description={"suggested_value": o.get(CONF_FIXED_DAILY)}): selector.NumberSelector(
                selector.NumberSelectorConfig(min=0, max=100, step=0.0001, mode=selector.NumberSelectorMode.BOX)),
            vol.Optional(CONF_FIXED_MONTHLY, description={"suggested_value": o.get(CONF_FIXED_MONTHLY)}): selector.NumberSelector(
                selector.NumberSelectorConfig(min=-1000, max=10000, step=0.01, mode=selector.NumberSelectorMode.BOX)),
            vol.Required(CONF_MAX_HOURLY_KWH, default=o.get(CONF_MAX_HOURLY_KWH, DEFAULT_MAX_HOURLY_KWH)): selector.NumberSelector(
                selector.NumberSelectorConfig(min=1, max=1000, step=1, mode=selector.NumberSelectorMode.BOX,
                                              unit_of_measurement="kWh")),
        }
        return self.async_show_form(step_id="init", data_schema=vol.Schema(schema))

    def _suggested_excluded_areas(self) -> list[str]:
        floors = fr.async_get(self.hass)
        out = []
        for area in ar.async_get(self.hass).async_list_areas():
            floor = floors.async_get_floor(area.floor_id) if area.floor_id else None
            if is_outdoor_name(area.name) or (floor and is_outdoor_name(floor.name)):
                out.append(area.id)
        return out
