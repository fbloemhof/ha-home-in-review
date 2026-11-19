"""On-time sensors for the boiler's hot-water and heating status (see gas.split_measured).

Binary sensors (and a thermostat's hvac_action) have no long-term statistics, and their history is purged after a
few days. These sensors add up the hours the chosen entity was active, as a ``total_increasing`` duration, so Home
Assistant keeps hourly statistics of them for good. Reports from the first full month after setting them up use
them to split gas into hot water and heating; earlier months keep the estimate from degree days.
"""
from __future__ import annotations

import datetime as dt

from homeassistant.components.sensor import RestoreSensor, SensorDeviceClass, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfTime
from homeassistant.core import Event, EventStateChangedData, HomeAssistant, State, callback
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import async_track_state_change_event, async_track_time_interval
from homeassistant.util import dt as dt_util

from .const import CONF_GAS_CH, CONF_GAS_DHW, DOMAIN

# sensor key -> option holding the entity it follows
ON_TIME = {"hot_water_time": CONF_GAS_DHW, "heating_time": CONF_GAS_CH}
TICK = dt.timedelta(minutes=1)


def is_active(state: State | None) -> bool:
    if state is None:
        return False
    if state.domain == "climate":
        return state.attributes.get("hvac_action") in ("heating", "preheating")
    return state.state == "on"


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    opts = entry.runtime_data.options
    wanted = {key: opts[conf] for key, conf in ON_TIME.items() if opts.get(conf)}
    # Sensors whose option was cleared are removed (their statistics stay in the database).
    reg = er.async_get(hass)
    keep = {f"{entry.entry_id}_{k}" for k in wanted}
    for ent in er.async_entries_for_config_entry(reg, entry.entry_id):
        if ent.domain == "sensor" and ent.unique_id not in keep:
            reg.async_remove(ent.entity_id)
    async_add_entities(OnTimeSensor(entry, key, source) for key, source in wanted.items())


class OnTimeSensor(RestoreSensor):
    _attr_has_entity_name = True
    _attr_device_class = SensorDeviceClass.DURATION
    _attr_state_class = SensorStateClass.TOTAL_INCREASING
    _attr_native_unit_of_measurement = UnitOfTime.HOURS
    _attr_suggested_display_precision = 1
    _attr_should_poll = False

    def __init__(self, entry: ConfigEntry, key: str, source: str) -> None:
        self._attr_unique_id = f"{entry.entry_id}_{key}"
        self._attr_translation_key = key
        self._attr_icon = "mdi:water-boiler" if key == "hot_water_time" else "mdi:radiator"
        self._attr_device_info = DeviceInfo(identifiers={(DOMAIN, entry.entry_id)}, name="Home in Review",
                                            entry_type=DeviceEntryType.SERVICE)
        self._attr_extra_state_attributes = {"source": source}
        self.source = source
        self.hours = 0.0
        self.since: dt.datetime | None = None

    @property
    def native_value(self) -> float:
        return round(self.hours + self._running(dt_util.utcnow()), 4)

    def _running(self, now: dt.datetime) -> float:
        return (now - self.since).total_seconds() / 3600 if self.since else 0.0

    def _bank(self, now: dt.datetime) -> None:
        """Add the time since the last bank to the total (while active)."""
        if self.since:
            self.hours += max(0.0, self._running(now))
            self.since = now

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        if (last := await self.async_get_last_sensor_data()) is not None:
            try:
                self.hours = max(0.0, float(last.native_value or 0))
            except (TypeError, ValueError):
                self.hours = 0.0
        if is_active(self.hass.states.get(self.source)):
            self.since = dt_util.utcnow()

        @callback
        def changed(event: Event[EventStateChangedData]) -> None:
            now = dt_util.utcnow()
            self._bank(now)
            self.since = now if is_active(event.data["new_state"]) else None
            self.async_write_ha_state()

        @callback
        def tick(now: dt.datetime) -> None:
            if self.since:
                self._bank(dt_util.utcnow())
                self.async_write_ha_state()

        self.async_on_remove(async_track_state_change_event(self.hass, [self.source], changed))
        self.async_on_remove(async_track_time_interval(self.hass, tick, TICK))
