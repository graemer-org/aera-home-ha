"""Diagnostics: raw Ayla property dump per diffuser."""

from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD
from homeassistant.core import HomeAssistant

from .coordinator import AeraConfigEntry

TO_REDACT = {CONF_EMAIL, CONF_PASSWORD, "mac", "lan_ip"}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: AeraConfigEntry
) -> dict[str, Any]:
    """Return the raw device and property data for troubleshooting."""
    data = entry.runtime_data.data
    return {
        "entry": async_redact_data(dict(entry.data), TO_REDACT),
        "devices": async_redact_data(
            {
                dsn: {
                    "oem_model": device.oem_model,
                    "device_type": device.device_type.value,
                    "product_name": device.product_name,
                    "is_online": device.is_online,
                    "mac": device.mac,
                    "lan_ip": device.lan_ip,
                    "properties": data.properties.get(dsn, {}),
                }
                for dsn, device in data.devices.items()
            },
            TO_REDACT,
        ),
    }
