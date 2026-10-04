"""Fixtures for Aera for Home tests.

The real `aera` library runs against canned Ayla/Contentful HTTP responses so the
integration is exercised end to end, minus the network.
"""

from __future__ import annotations

from collections.abc import Generator
import json
from typing import Any

from aera.const import DEVICE_SERVICE_URL, USER_SERVICE_URL
from aera.contentful import CONTENTFUL_BASE_URL
from aioresponses import aioresponses
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry
from yarl import URL

from homeassistant.const import CONF_EMAIL, CONF_PASSWORD
from homeassistant.core import HomeAssistant

from custom_components.aera.const import DOMAIN

EMAIL = "user@example.com"
PASSWORD = "hunter2"

FULL_DSN = "AC000W000000001"
MINI_DSN = "AC000W000000002"

SIGN_IN_URL = f"{USER_SERVICE_URL}/users/sign_in.json"
REFRESH_URL = f"{USER_SERVICE_URL}/users/refresh_token.json"
DEVICES_URL = f"{DEVICE_SERVICE_URL}/apiv1/devices.json"
METADATA_URL = f"{USER_SERVICE_URL}/api/v1/users/data/device_data_table.json"
CONTENTFUL_URL = f"{CONTENTFUL_BASE_URL}/entries?content_type=fragrance&limit=100&skip=0"

DEVICES = [
    {
        "device": {
            "dsn": FULL_DSN,
            "key": 1001,
            "product_name": "Aera 3.1",
            "oem_model": "aera31",
            "model": "AY028MHA1",
            "connection_status": "Online",
            "mac": "aabbccddeeff",
        }
    },
    {
        "device": {
            "dsn": MINI_DSN,
            "key": 1002,
            "product_name": "Aera Mini",
            "oem_model": "aeraMini",
            "model": "AY028MHA1",
            "connection_status": "Online",
            "mac": "aabbccddee00",
        }
    },
]

METADATA = {
    "datum": {
        "value": json.dumps(
            [
                {"dsn": FULL_DSN, "room_name": "Living Room"},
                {"dsn": MINI_DSN, "room_name": "Bedroom"},
            ]
        )
    }
}

PROPERTIES: dict[str, dict[str, Any]] = {
    FULL_DSN: {
        "power_state": 1,
        "intensity_state": 6,
        "cartridge_usage": 30,
        "cartridge_present": 1,
        "fragrance_name": "Wood Sage",
        "error_condition": 0,
        "session_state": 0,
        "session_time_left": 0,
        "device_fw_version": "3.1.0",
    },
    MINI_DSN: {
        "power_state": 0,
        "intensity_state": 3,
        "set_fragrance_identifier": "LAV",
        "pump_life_time": 7200,
        "pump_life_time_qr_scanned": 0,
        "error_condition": 0,
        "session_state": 0,
        "session_time_left": 0,
    },
}

CONTENTFUL = {
    "total": 3,
    "items": [
        {"fields": {"fragranceName": "Wood Sage & Sea Salt", "firmwareName": "Wood Sage"}},
        {
            "fields": {
                "fragranceName": "Lavender",
                "fragranceId": "LAV",
                "fragranceQr": "qr-lav",
                "miniFill": 10,
                "miniOutput": 0.5,
            }
        },
        {
            "fields": {
                "fragranceName": "Fig Tree",
                "fragranceId": "FIG",
                "fragranceQr": "qr-fig",
                "miniFill": 10,
                "miniOutput": 0.5,
            }
        },
    ],
}

TOKENS = {"access_token": "access", "refresh_token": "refresh"}


def properties_url(dsn: str) -> str:
    """Return the property list URL for a DSN."""
    return f"{DEVICE_SERVICE_URL}/apiv1/dsns/{dsn}/properties.json"


def datapoint_url(dsn: str, prop: str) -> str:
    """Return the datapoint URL for a property."""
    return f"{DEVICE_SERVICE_URL}/apiv1/dsns/{dsn}/properties/{prop}/datapoints.json"


def property_payload(props: dict[str, Any]) -> list[dict[str, Any]]:
    """Wrap a name -> value mapping as Ayla returns it."""
    return [{"property": {"name": name, "value": value}} for name, value in props.items()]


def sent_values(mock: aioresponses, dsn: str, prop: str) -> list[Any]:
    """Return every value POSTed to a property, oldest first."""
    calls = mock.requests.get(("POST", URL(datapoint_url(dsn, prop))), [])
    return [call.kwargs["json"]["datapoint"]["value"] for call in calls]


def register_cloud(mock: aioresponses) -> None:
    """Register a healthy Ayla + Contentful backend."""
    mock.post(SIGN_IN_URL, payload=TOKENS, repeat=True)
    mock.get(DEVICES_URL, payload=DEVICES, repeat=True)
    mock.get(METADATA_URL, payload=METADATA, repeat=True)
    mock.get(CONTENTFUL_URL, payload=CONTENTFUL, repeat=True)
    for dsn, props in PROPERTIES.items():
        mock.get(properties_url(dsn), payload=property_payload(props), repeat=True)
        for prop in (
            "set_power_state",
            "set_intensity_manual",
            "set_session_length",
            "set_fragrance_identifier",
        ):
            mock.post(datapoint_url(dsn, prop), status=201, payload={}, repeat=True)


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations: None) -> None:
    """Load custom_components/ in every test."""


@pytest.fixture
def cloud() -> Generator[aioresponses]:
    """Intercept HTTP with an empty mock (tests register what they need)."""
    with aioresponses() as mock:
        yield mock


@pytest.fixture
def healthy_cloud(cloud: aioresponses) -> aioresponses:
    """Intercept HTTP with a working backend."""
    register_cloud(cloud)
    return cloud


@pytest.fixture
def config_entry(hass: HomeAssistant) -> MockConfigEntry:
    """Return a config entry added to hass."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title=EMAIL,
        unique_id=EMAIL,
        data={CONF_EMAIL: EMAIL, CONF_PASSWORD: PASSWORD},
    )
    entry.add_to_hass(hass)
    return entry


@pytest.fixture
async def setup_integration(
    hass: HomeAssistant, config_entry: MockConfigEntry, healthy_cloud: aioresponses
) -> MockConfigEntry:
    """Set up the integration against the healthy backend."""
    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()
    return config_entry
