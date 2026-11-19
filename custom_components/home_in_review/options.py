"""Validation of stored options.

The options form already validates input, but stored options can come from an older version or be edited by
hand. Everything the collector uses goes through sanitize(): wrong types are dropped or clamped, unsafe URLs are
left out, and long texts are cut.
"""
from __future__ import annotations

import datetime as dt
import logging
import re
from typing import Any

from .const import (
    CONF_AI_INSTRUCTIONS,
    CONF_AI_TASK,
    CONF_CAR_CHARGERS,
    CONF_CAR_ODOMETERS,
    CONF_DD_BASE,
    CONF_DD_WEIGHTED,
    CONF_EVCC_URL,
    CONF_EXCLUDED_AREAS,
    CONF_FIXED_DAILY,
    CONF_FIXED_MONTHLY,
    CONF_GAS_BASE,
    CONF_GAS_CH,
    CONF_GAS_DHW,
    CONF_HP_DEVICES,
    CONF_HP_HEAT,
    CONF_MAX_HOURLY_KWH,
    CONF_NOTIFY,
    CONF_OUTDOOR_SENSOR,
    CONF_RAIN_SENSOR,
    CONF_REPORT_DAY,
    CONF_REPORT_TIME,
    CONF_THEME,
    CONF_TILES,
    CONF_TM_HOME,
    CONF_TM_TOKEN,
    CONF_TM_URL,
    CONF_USE_OPEN_METEO,
    CONF_YEAR_START,
)
from .extras import TILE_TYPES
from .net import check_url

_LOGGER = logging.getLogger(__name__)

MAX_AI_INSTRUCTIONS = 1000
MAX_NAME = 80
MAX_TILES = 30
ENTITY_ID = re.compile(r"^[a-z_]+\.[a-z0-9_]+$")
STATISTIC_ID = re.compile(r"^([a-z_]+\.[a-z0-9_]+|[a-z0-9_]+:[a-zA-Z0-9_]+)$")


def _entity(v: Any) -> str | None:
    return v if isinstance(v, str) and ENTITY_ID.match(v) else None


def _entities(v: Any) -> list[str]:
    if isinstance(v, str):
        v = [v]
    return [x for x in v if _entity(x)] if isinstance(v, list) else []


def _number(v: Any, lo: float, hi: float) -> float | None:
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return min(hi, max(lo, f))


def _text(v: Any, limit: int) -> str | None:
    return v.strip()[:limit] if isinstance(v, str) and v.strip() else None


def sanitize(raw: dict) -> dict:
    o: dict[str, Any] = {k: v for k, v in raw.items() if k in ("backfill_months", "backfilled", "admin_only")}
    o[CONF_NOTIFY] = [x for x in raw.get(CONF_NOTIFY) or [] if isinstance(x, str) and re.match(r"^[a-z_]+(\.[a-z0-9_]+)?$", x)]
    if (d := _number(raw.get(CONF_REPORT_DAY), 1, 28)) is not None:
        o[CONF_REPORT_DAY] = int(d)
    try:
        if raw.get(CONF_REPORT_TIME):
            o[CONF_REPORT_TIME] = dt.time.fromisoformat(str(raw[CONF_REPORT_TIME])).isoformat()
    except ValueError:
        pass
    if (y := _number(raw.get(CONF_YEAR_START), 1, 12)) is not None:
        o[CONF_YEAR_START] = int(y)
    if raw.get(CONF_EXCLUDED_AREAS) is not None:
        o[CONF_EXCLUDED_AREAS] = [x for x in raw[CONF_EXCLUDED_AREAS] if isinstance(x, str)] if isinstance(
            raw[CONF_EXCLUDED_AREAS], list) else []
    for k in (CONF_OUTDOOR_SENSOR, CONF_RAIN_SENSOR, CONF_AI_TASK, CONF_GAS_DHW, CONF_GAS_CH):
        if _entity(raw.get(k)):
            o[k] = raw[k]
    for k in (CONF_HP_DEVICES, CONF_HP_HEAT, CONF_CAR_ODOMETERS, CONF_CAR_CHARGERS):
        if v := _entities(raw.get(k)):
            o[k] = v
    if raw.get(CONF_THEME) in ("auto", "light", "dark", "night", "mono", "ha"):
        o[CONF_THEME] = raw[CONF_THEME]
    if (b := _number(raw.get(CONF_DD_BASE), -10, 80)) is not None:
        o[CONF_DD_BASE] = b
    if raw.get(CONF_DD_WEIGHTED) is not None:
        o[CONF_DD_WEIGHTED] = bool(raw[CONF_DD_WEIGHTED])
    if raw.get(CONF_USE_OPEN_METEO) is not None:
        o[CONF_USE_OPEN_METEO] = bool(raw[CONF_USE_OPEN_METEO])
    for k, lo, hi in ((CONF_GAS_BASE, 0, 1000), (CONF_FIXED_DAILY, -100, 100), (CONF_FIXED_MONTHLY, -1000, 10000), (CONF_MAX_HOURLY_KWH, 1, 1000)):
        if (v := _number(raw.get(k), lo, hi)) is not None:
            o[k] = v
    if raw.get(CONF_EVCC_URL):
        if check_url(str(raw[CONF_EVCC_URL]), carries_token=False) is None:
            o[CONF_EVCC_URL] = str(raw[CONF_EVCC_URL]).strip()
        else:
            _LOGGER.warning("Ignoring the evcc address: it is not a valid http(s) address")
    if raw.get(CONF_TM_URL) and raw.get(CONF_TM_TOKEN):
        if check_url(str(raw[CONF_TM_URL]), carries_token=True) is None and isinstance(raw[CONF_TM_TOKEN], str):
            o[CONF_TM_URL] = str(raw[CONF_TM_URL]).strip()
            o[CONF_TM_TOKEN] = raw[CONF_TM_TOKEN].strip()[:512]
            if home := _text(raw.get(CONF_TM_HOME), MAX_NAME):
                o[CONF_TM_HOME] = home
        else:
            _LOGGER.warning("Ignoring the TeslaMate settings: the address is not acceptable for sending a token")
    if instr := _text(raw.get(CONF_AI_INSTRUCTIONS), MAX_AI_INSTRUCTIONS):
        o[CONF_AI_INSTRUCTIONS] = instr
    tiles = []
    for t in (raw.get(CONF_TILES) or [])[:MAX_TILES]:
        if not isinstance(t, dict) or t.get("type") not in TILE_TYPES:
            continue
        sid = t.get("statistic")
        if not isinstance(sid, str) or not STATISTIC_ID.match(sid):
            continue
        tile: dict[str, Any] = {"name": _text(t.get("name"), MAX_NAME) or sid, "statistic": sid, "type": t["type"],
                                "unit": _text(t.get("unit"), 20) or "", "decimals": int(_number(t.get("decimals"), 0, 3) or 0)}
        if (thr := _number(t.get("threshold"), -1e9, 1e9)) is not None:
            tile["threshold"] = thr
        if (rh := _number(t.get("run_hours"), 0.5, 24)) is not None:
            tile["run_hours"] = rh
        tiles.append(tile)
    if tiles:
        o[CONF_TILES] = tiles
    return o
