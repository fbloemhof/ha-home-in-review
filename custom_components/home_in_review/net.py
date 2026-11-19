"""Checks for the user-configured outside addresses (TeslaMate's Grafana, evcc).

A token is only ever sent to the exact host the user entered: only http(s), no credentials in the URL, and
requests that carry a token don't follow redirects. Plain http is accepted for addresses on the local network
(that's how TeslaMate and evcc usually run); a token to a public address needs https.
"""
from __future__ import annotations

import ipaddress
from urllib.parse import urlsplit


def is_local_host(host: str) -> bool:
    host = host.strip("[]").lower()
    if host in ("localhost",) or host.endswith((".local", ".lan", ".home", ".internal", ".home.arpa")) or "." not in host:
        return True
    try:
        ip = ipaddress.ip_address(host)
    except ValueError:
        return False
    return ip.is_private or ip.is_loopback or ip.is_link_local


def check_url(url: str, carries_token: bool) -> str | None:
    """None when the URL is acceptable, otherwise an error key for the options form."""
    try:
        parts = urlsplit(url.strip())
        _ = parts.port  # raises ValueError for a malformed port
    except ValueError:
        return "invalid_url"
    if parts.scheme not in ("http", "https") or not parts.hostname:
        return "invalid_url"
    if parts.username or parts.password:
        return "url_credentials"
    if parts.query or parts.fragment:
        return "invalid_url"
    if carries_token and parts.scheme == "http" and not is_local_host(parts.hostname):
        return "https_required"
    return None


def base_url(url: str) -> str:
    """Normalised base URL without a trailing slash."""
    return url.strip().rstrip("/")
