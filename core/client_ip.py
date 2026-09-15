"""Client IP extraction with an explicit trusted-proxy boundary."""

from __future__ import annotations

from typing import Any


def _csv(value: str) -> set[str]:
    return {part.strip() for part in (value or "").split(",") if part.strip()}


def get_client_ip(request: Any, settings: Any) -> str:
    """Return the direct IP, or X-Forwarded-For only from a trusted proxy."""
    direct_ip = getattr(getattr(request, "client", None), "host", None) or "unknown"
    trusted_proxy_ips = _csv(getattr(settings, "trusted_proxy_ips", ""))
    if not getattr(settings, "trust_proxy_headers", False) or direct_ip not in trusted_proxy_ips:
        return direct_ip

    forwarded = request.headers.get("x-forwarded-for", "")
    first_hop = forwarded.split(",", 1)[0].strip()
    return first_hop or direct_ip
