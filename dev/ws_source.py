"""Development data source: talks to a running Home Assistant over the WebSocket API.

Lets the collector run outside Home Assistant against real data:
    HA_URL=http://homeassistant.local:8123 HA_TOKEN=... python dev/run.py 2026-10
(Inside the VS Code / SSH add-on, SUPERVISOR_TOKEN and http://supervisor/core are used automatically.)
"""
from __future__ import annotations

import os

import aiohttp

CLIMATE_CLASSES = ("temperature", "humidity", "carbon_dioxide")


class WsSource:
    def __init__(self, session: aiohttp.ClientSession) -> None:
        self.session = session
        self.url = os.environ.get("HA_URL", "http://supervisor/core").rstrip("/")
        self.token = os.environ.get("HA_TOKEN") or os.environ["SUPERVISOR_TOKEN"]
        self.ws = None
        self.n = 0

    async def __aenter__(self):
        self.ws = await self.session.ws_connect(self.url + "/websocket", max_msg_size=0)
        await self.ws.receive_json()
        await self.ws.send_json({"type": "auth", "access_token": self.token})
        if (await self.ws.receive_json()).get("type") != "auth_ok":
            raise RuntimeError("authentication failed")
        return self

    async def __aexit__(self, *exc):
        await self.ws.close()

    async def call(self, msg: dict):
        self.n += 1
        msg = {**msg, "id": self.n}
        await self.ws.send_json(msg)
        while True:
            r = await self.ws.receive_json()
            if r.get("id") == self.n:
                if not r.get("success", True):
                    raise RuntimeError(r.get("error"))
                return r.get("result")

    async def config(self):
        c = await self.call({"type": "get_config"})
        us = c["unit_system"].get("temperature") == "°F"
        return {"time_zone": c["time_zone"], "latitude": c["latitude"], "longitude": c["longitude"],
                "currency": c["currency"], "unit_system": "us_customary" if us else "metric", "language": c["language"],
                "location_name": c.get("location_name")}

    async def energy_prefs(self):
        try:
            return await self.call({"type": "energy/get_prefs"})
        except RuntimeError:
            return None

    async def statistics_meta(self, ids):
        res = await self.call({"type": "recorder/get_statistics_metadata", "statistic_ids": sorted(ids)})
        return {m["statistic_id"]: {"unit": m.get("statistics_unit_of_measurement"), "unit_class": m.get("unit_class")}
                for m in res}

    async def statistics(self, ids, start, end, period, units, types):
        res = await self.call({"type": "recorder/statistics_during_period", "statistic_ids": sorted(ids),
                               "start_time": start.isoformat(), "end_time": end.isoformat(), "period": period,
                               "units": units, "types": sorted(types)})
        for rows in res.values():
            for r in rows:
                r["start"] = r["start"] / 1000
        return res

    async def climate_sensors(self):
        states = await self.call({"type": "get_states"})
        ents = {e["entity_id"]: e for e in await self.call({"type": "config/entity_registry/list"})}
        devs = {d["id"]: d for d in await self.call({"type": "config/device_registry/list"})}
        areas = {a["area_id"]: a for a in await self.call({"type": "config/area_registry/list"})}
        floors = {f["floor_id"]: f for f in await self.call({"type": "config/floor_registry/list"})}
        out = []
        for s in states:
            a = s["attributes"]
            if not s["entity_id"].startswith("sensor.") or a.get("state_class") != "measurement":
                continue
            if a.get("device_class") not in CLIMATE_CLASSES:
                continue
            e = ents.get(s["entity_id"]) or {}
            if e.get("disabled_by") or e.get("entity_category"):
                continue
            area_id = e.get("area_id") or (devs.get(e.get("device_id")) or {}).get("area_id")
            area = areas.get(area_id) or {}
            out.append({"entity_id": s["entity_id"], "name": a.get("friendly_name"), "device_class": a["device_class"],
                        "device_id": e.get("device_id"),
                        "area_id": area_id, "area_name": area.get("name"),
                        "floor_name": (floors.get(area.get("floor_id")) or {}).get("name")})
        return out

    async def device_names(self, ids):
        out = await self.names(ids)
        ents = {e["entity_id"]: e for e in await self.call({"type": "config/entity_registry/list"})}
        devs = {d["id"]: d for d in await self.call({"type": "config/device_registry/list"})}
        for i in ids:
            d = devs.get((ents.get(i) or {}).get("device_id"))
            if d:
                out[i] = d.get("name_by_user") or d.get("name") or out.get(i, i)
        return out

    async def names(self, ids):
        states = await self.call({"type": "get_states"})
        return {x["entity_id"]: x["attributes"].get("friendly_name") for x in states
                if x["entity_id"] in ids and x["attributes"].get("friendly_name")}

    async def areas(self):
        floors = {f["floor_id"]: f["name"] for f in await self.call({"type": "config/floor_registry/list"})}
        return [{"area_id": a["area_id"], "name": a["name"], "floor_name": floors.get(a.get("floor_id"))}
                for a in await self.call({"type": "config/area_registry/list"})]

    async def request_json(self, method, url, headers=None, json=None):
        async with self.session.request(method, url, headers=headers, json=json, allow_redirects=False,
                                        timeout=aiohttp.ClientTimeout(total=60)) as r:
            if 300 <= r.status < 400:
                raise RuntimeError("redirect not followed")
            r.raise_for_status()
            return await r.json()

    async def ai_generate(self, entity_id, instructions):
        res = await self.call({"type": "call_service", "domain": "ai_task", "service": "generate_data",
                               "service_data": {"task_name": "Home in Review", "entity_id": entity_id,
                                                "instructions": instructions},
                               "return_response": True})
        return ((res or {}).get("response") or {}).get("data")

    async def fetch_json(self, url, allow_redirects=True):
        async with self.session.get(url, allow_redirects=allow_redirects, timeout=aiohttp.ClientTimeout(total=120)) as r:
            if 300 <= r.status < 400:
                raise RuntimeError("redirect not followed")
            r.raise_for_status()
            return await r.json()
