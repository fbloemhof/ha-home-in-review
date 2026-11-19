"""Month documents on disk (<config>/home_in_review/), with an in-memory copy for rendering."""
from __future__ import annotations

import json
import logging
import os
import tempfile
from pathlib import Path
from typing import Any

from homeassistant.core import HomeAssistant

from .const import STORAGE_DIR

_LOGGER = logging.getLogger(__name__)


def write_atomic(path: Path, text: str) -> None:
    """Write via a temporary file in the same directory and rename it over the target, so an interrupted write
    never leaves a half-written report behind."""
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(text)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise


class ReportStore:
    def __init__(self, hass: HomeAssistant) -> None:
        self.hass = hass
        self.dir = Path(hass.config.path(STORAGE_DIR))
        self.docs: dict[str, dict] = {}
        self.cache: dict[str, Any] = {}

    def _load(self) -> None:
        self.dir.mkdir(exist_ok=True)
        for p in self.dir.glob("????-??.json"):
            try:
                doc = json.loads(p.read_text(encoding="utf-8"))
            except (OSError, ValueError) as err:
                _LOGGER.warning("Skipping unreadable report %s: %s", p.name, err)
                continue
            if isinstance(doc, dict) and isinstance(doc.get("period"), dict) and isinstance(doc.get("units"), dict):
                self.docs[p.stem] = doc
            else:
                _LOGGER.warning("Skipping report %s: not in the expected format", p.name)
        cache = self.dir / "cache.json"
        if cache.exists():
            try:
                loaded = json.loads(cache.read_text(encoding="utf-8"))
                self.cache = loaded if isinstance(loaded, dict) else {}
            except (OSError, ValueError):
                self.cache = {}

    async def async_load(self) -> None:
        await self.hass.async_add_executor_job(self._load)

    async def async_save(self, ym: str, doc: dict) -> None:
        self.docs[ym] = doc
        text = json.dumps(doc, ensure_ascii=False, indent=1)
        cache = json.dumps(self.cache)

        def write() -> None:
            self.dir.mkdir(exist_ok=True)
            write_atomic(self.dir / f"{ym}.json", text)
            write_atomic(self.dir / "cache.json", cache)

        await self.hass.async_add_executor_job(write)
