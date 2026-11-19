"""The report pages (served by Home Assistant's HTTP server): GET /api/home_in_review/report/<YYYY-MM | year-YYYY-MM | index> -> HTML.

Requires a logged-in Home Assistant user, or a short-lived signed path (the sidebar panel uses auth/sign_path).
With the "administrators only" option, other users get 403. The pages may not load or send anything elsewhere
(Content-Security-Policy), and may only be framed by Home Assistant itself.
"""
from __future__ import annotations

import re

from aiohttp import web
from homeassistant.components.http import KEY_HASS_USER, HomeAssistantView
from homeassistant.core import HomeAssistant

from . import render
from .const import CONF_ADMIN_ONLY, CONF_YEAR_START, DOMAIN, URL_BASE

YM = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")
LANG = re.compile(r"^[a-z]{2}(-[A-Za-z]{2,4})?$")
HEADERS = {
    "Cache-Control": "no-store",
    "X-Content-Type-Options": "nosniff",
    "Referrer-Policy": "no-referrer",
    # Inline styles and scripts only; nothing from elsewhere, no outgoing requests, framed only by Home Assistant.
    "Content-Security-Policy": ("default-src 'none'; style-src 'unsafe-inline'; script-src 'unsafe-inline'; "
                                "img-src data:; base-uri 'none'; form-action 'none'; frame-ancestors 'self'"),
}


class ReportView(HomeAssistantView):
    url = URL_BASE + "/report/{name}"
    name = "api:home_in_review:report"
    requires_auth = True

    async def get(self, request: web.Request, name: str) -> web.Response:
        hass: HomeAssistant = request.app["hass"]
        entries = hass.config_entries.async_loaded_entries(DOMAIN)
        if not entries:
            return web.Response(status=404)
        rt = entries[0].runtime_data
        user = request.get(KEY_HASS_USER)
        if rt.options.get(CONF_ADMIN_ONLY) and not (user and user.is_admin):
            return web.Response(status=403)
        docs = rt.store.docs
        lang = request.query.get("lang", "")
        lang = lang if LANG.match(lang) else hass.config.language
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
        return web.Response(text=html, content_type="text/html", charset="utf-8", headers=HEADERS)
