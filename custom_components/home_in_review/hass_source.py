"""Data source backed by a running Home Assistant (recorder, energy manager, registries)."""
from __future__ import annotations

import datetime as dt
from typing import Any

import aiohttp
from homeassistant.components.recorder import get_instance
from homeassistant.components.recorder.statistics import (
    get_metadata,
    statistics_during_period,
)
from homeassistant.const import UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers import area_registry as ar
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers import floor_registry as fr
from homeassistant.helpers.aiohttp_client import async_get_clientsession

CLIMATE_CLASSES = ("temperature", "humidity", "carbon_dioxide")


class HassSource:
    def __init__(self, hass: HomeAssistant) -> None:
        self.hass = hass

    async def config(self) -> dict[str, Any]:
        c = self.hass.config
        return {
            "time_zone": c.time_zone,
            "latitude": c.latitude,
            "longitude": c.longitude,
            "currency": c.currency,
            "unit_system": "us_customary" if c.units.temperature_unit == UnitOfTemperature.FAHRENHEIT else "metric",
            "language": c.language,
            "location_name": c.location_name,
        }

    async def energy_prefs(self) -> dict | None:
        try:
            from homeassistant.components.energy.data import async_get_manager
        except ImportError:  # energy integration not available
            return None
        manager = await async_get_manager(self.hass)
        return manager.data

    async def statistics_meta(self, ids: set[str]) -> dict[str, dict]:
        meta = await get_instance(self.hass).async_add_executor_job(
            lambda: get_metadata(self.hass, statistic_ids=set(ids)))
        return {sid: {"unit": m.get("unit_of_measurement"), "unit_class": m.get("unit_class")} for sid, (_, m) in meta.items()}

    async def statistics(self, ids: set[str], start: dt.datetime, end: dt.datetime, period: str,
                         units: dict, types: set[str]) -> dict[str, list[dict]]:
        res = await get_instance(self.hass).async_add_executor_job(
            statistics_during_period, self.hass, start, end, set(ids), period, units, set(types))
        return {sid: [dict(r) for r in rows] for sid, rows in res.items()}

    async def climate_sensors(self) -> list[dict]:
        ents = er.async_get(self.hass)
        devs = dr.async_get(self.hass)
        areas = ar.async_get(self.hass)
        floors = fr.async_get(self.hass)
        out = []
        for state in self.hass.states.async_all("sensor"):
            a = state.attributes
            if a.get("state_class") != "measurement" or a.get("device_class") not in CLIMATE_CLASSES:
                continue
            entry = ents.async_get(state.entity_id)
            if entry and (entry.disabled_by or entry.entity_category):
                continue
            device = devs.async_get(entry.device_id) if entry and entry.device_id else None
            area_id = (entry.area_id if entry else None) or (device.area_id if device else None)
            area = areas.async_get_area(area_id) if area_id else None
            floor = floors.async_get_floor(area.floor_id) if area and area.floor_id else None
            out.append({"entity_id": state.entity_id, "name": a.get("friendly_name"), "device_class": a["device_class"],
                        "device_id": entry.device_id if entry else None, "area_id": area_id,
                        "area_name": area.name if area else None, "floor_name": floor.name if floor else None})
        return out

    async def areas(self) -> list[dict]:
        floors = fr.async_get(self.hass)
        out = []
        for area in ar.async_get(self.hass).async_list_areas():
            floor = floors.async_get_floor(area.floor_id) if area.floor_id else None
            out.append({"area_id": area.id, "name": area.name, "floor_name": floor.name if floor else None})
        return out

    async def fetch_json(self, url: str) -> Any:
        session = async_get_clientsession(self.hass)
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=120)) as resp:
            resp.raise_for_status()
            return await resp.json()
