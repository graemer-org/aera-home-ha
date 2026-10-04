"""Tests for setup, polling and auth handling."""

from __future__ import annotations

from aioresponses import aioresponses
from freezegun.api import FrozenDateTimeFactory
from pytest_homeassistant_custom_component.common import MockConfigEntry, async_fire_time_changed

from homeassistant.config_entries import SOURCE_REAUTH, ConfigEntryState
from homeassistant.const import STATE_UNAVAILABLE
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr

from custom_components.aera.const import DOMAIN, SCAN_INTERVAL

from .conftest import (
    DEVICES,
    DEVICES_URL,
    FULL_DSN,
    REFRESH_URL,
    SIGN_IN_URL,
    TOKENS,
    register_cloud,
)


async def test_setup_creates_devices(
    hass: HomeAssistant, setup_integration: MockConfigEntry, device_registry: dr.DeviceRegistry
) -> None:
    """Each diffuser becomes a device keyed by DSN."""
    # Arrange
    entry = setup_integration

    # Act
    device = device_registry.async_get_device(identifiers={(DOMAIN, FULL_DSN)})

    # Assert
    assert entry.state is ConfigEntryState.LOADED
    assert device is not None
    assert device.name == "Living Room"
    assert device.model == "Aera 3.1"
    assert device.model_id == "aera31"
    assert device.serial_number == FULL_DSN
    assert device.sw_version == "3.1.0"


async def test_setup_bad_credentials_starts_reauth(
    hass: HomeAssistant, config_entry: MockConfigEntry, cloud: aioresponses
) -> None:
    """A rejected login on startup asks the user to reauthenticate."""
    # Arrange
    cloud.post(SIGN_IN_URL, status=401, repeat=True)

    # Act
    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    # Assert
    assert config_entry.state is ConfigEntryState.SETUP_ERROR
    flows = hass.config_entries.flow.async_progress_by_handler(DOMAIN)
    assert [flow["context"]["source"] for flow in flows] == [SOURCE_REAUTH]


async def test_setup_cloud_down_retries(
    hass: HomeAssistant, config_entry: MockConfigEntry, cloud: aioresponses
) -> None:
    """A transport error on startup retries later."""
    # Arrange
    cloud.post(SIGN_IN_URL, exception=TimeoutError(), repeat=True)

    # Act
    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    # Assert
    assert config_entry.state is ConfigEntryState.SETUP_RETRY


async def test_unload(hass: HomeAssistant, setup_integration: MockConfigEntry) -> None:
    """The entry unloads cleanly."""
    # Arrange
    entry = setup_integration

    # Act
    await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()

    # Assert
    assert entry.state is ConfigEntryState.NOT_LOADED


async def test_expired_session_logs_in_again(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    cloud: aioresponses,
    freezer: FrozenDateTimeFactory,
) -> None:
    """When both tokens are dead the coordinator does a fresh login."""
    # Arrange
    cloud.post(SIGN_IN_URL, payload=TOKENS)
    cloud.get(DEVICES_URL, status=401)
    cloud.post(REFRESH_URL, status=401)
    register_cloud(cloud)
    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    # Act
    freezer.tick(SCAN_INTERVAL)
    async_fire_time_changed(hass)
    await hass.async_block_till_done(wait_background_tasks=True)

    # Assert
    assert config_entry.state is ConfigEntryState.LOADED
    assert hass.states.get("fan.living_room").state == "on"
    assert not hass.config_entries.flow.async_progress_by_handler(DOMAIN)


async def test_password_changed_while_running_starts_reauth(
    hass: HomeAssistant,
    setup_integration: MockConfigEntry,
    cloud: aioresponses,
    freezer: FrozenDateTimeFactory,
) -> None:
    """Token refresh and re-login both failing triggers reauth."""
    # Arrange
    cloud.clear()
    cloud.get(DEVICES_URL, status=401, repeat=True)
    cloud.post(REFRESH_URL, status=401, repeat=True)
    cloud.post(SIGN_IN_URL, status=401, repeat=True)

    # Act
    freezer.tick(SCAN_INTERVAL)
    async_fire_time_changed(hass)
    await hass.async_block_till_done(wait_background_tasks=True)

    # Assert
    flows = hass.config_entries.flow.async_progress_by_handler(DOMAIN)
    assert [flow["context"]["source"] for flow in flows] == [SOURCE_REAUTH]
    assert hass.states.get("fan.living_room").state == STATE_UNAVAILABLE


async def test_offline_device_is_unavailable_but_connectivity_reports(
    hass: HomeAssistant,
    setup_integration: MockConfigEntry,
    cloud: aioresponses,
    freezer: FrozenDateTimeFactory,
) -> None:
    """An offline diffuser greys out controls but shows disconnected."""
    # Arrange
    offline = [{"device": {**item["device"], "connection_status": "Offline"}} for item in DEVICES]
    cloud.clear()
    cloud.get(DEVICES_URL, payload=offline, repeat=True)
    register_cloud(cloud)

    # Act
    freezer.tick(SCAN_INTERVAL)
    async_fire_time_changed(hass)
    await hass.async_block_till_done(wait_background_tasks=True)

    # Assert
    assert hass.states.get("fan.living_room").state == STATE_UNAVAILABLE
    assert hass.states.get("binary_sensor.living_room_connectivity").state == "off"
