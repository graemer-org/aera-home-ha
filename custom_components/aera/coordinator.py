"""DataUpdateCoordinator for the Aera for Home integration."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable
from dataclasses import dataclass, field
from typing import Any

from aera import AeraApi, AeraDevice
from aera.api import AeraApiError, AeraAuthError
import aiohttp

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, HomeAssistantError
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DOMAIN, LOGGER, REQUEST_TIMEOUT, SCAN_INTERVAL

type AeraConfigEntry = ConfigEntry[AeraCoordinator]

CONNECTION_ERRORS = (AeraApiError, aiohttp.ClientError, TimeoutError)


@dataclass
class AeraData:
    """Snapshot of all diffusers on the account."""

    devices: dict[str, AeraDevice]
    properties: dict[str, dict[str, Any]]
    mini_fragrances: list[dict[str, str | None]] = field(default_factory=list)


class AeraCoordinator(DataUpdateCoordinator[AeraData]):
    """Polls the Ayla cloud for device state."""

    config_entry: AeraConfigEntry

    def __init__(self, hass: HomeAssistant, entry: AeraConfigEntry, api: AeraApi) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            LOGGER,
            config_entry=entry,
            name=DOMAIN,
            update_interval=SCAN_INTERVAL,
        )
        self.api = api
        # Session length per DSN, owned by the session duration number entity.
        self.session_minutes: dict[str, int] = {}

    async def _async_setup(self) -> None:
        """Log in once before the first refresh."""
        await self._async_login()

    async def _async_login(self) -> None:
        try:
            async with asyncio.timeout(REQUEST_TIMEOUT):
                await self.api.login()
        except AeraAuthError as err:
            raise ConfigEntryAuthFailed(str(err)) from err
        except CONNECTION_ERRORS as err:
            raise UpdateFailed(f"Error connecting to Aera: {err}") from err

    async def _async_update_data(self) -> AeraData:
        try:
            return await self._async_fetch()
        except AeraAuthError:
            # The library already tried a token refresh on 401; fall back to a full login.
            LOGGER.debug("Aera token rejected, logging in again")
        except CONNECTION_ERRORS as err:
            raise UpdateFailed(f"Error communicating with Aera: {err}") from err

        await self._async_login()
        try:
            return await self._async_fetch()
        except AeraAuthError as err:
            raise ConfigEntryAuthFailed(str(err)) from err
        except CONNECTION_ERRORS as err:
            raise UpdateFailed(f"Error communicating with Aera: {err}") from err

    async def _async_fetch(self) -> AeraData:
        async with asyncio.timeout(REQUEST_TIMEOUT):
            devices = await self.api.get_devices()
            properties = await asyncio.gather(
                *(self.api.get_device_properties(device) for device in devices)
            )
            mini_fragrances: list[dict[str, str | None]] = []
            if any(device.device_type.is_mini for device in devices):
                mini_fragrances = await self.api.get_mini_fragrances()
        return AeraData(
            devices={device.dsn: device for device in devices},
            properties={
                device.dsn: props for device, props in zip(devices, properties, strict=True)
            },
            mini_fragrances=mini_fragrances,
        )

    async def async_command(self, command: Awaitable[bool]) -> None:
        """Run a device command, translating library errors for the service caller."""
        try:
            async with asyncio.timeout(REQUEST_TIMEOUT):
                await command
        except AeraAuthError as err:
            self.config_entry.async_start_reauth(self.hass)
            raise HomeAssistantError(f"Aera authentication failed: {err}") from err
        except CONNECTION_ERRORS as err:
            raise HomeAssistantError(f"Error sending command to Aera: {err}") from err
