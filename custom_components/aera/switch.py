"""Switch platform: timed fragrance session."""

from __future__ import annotations

from typing import Any

from aera.const import PROP_SESSION_STATE

from homeassistant.components.switch import SwitchEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import DEFAULT_SESSION_MINUTES
from .coordinator import AeraConfigEntry, AeraCoordinator
from .entity import AeraEntity

PARALLEL_UPDATES = 1


async def async_setup_entry(
    hass: HomeAssistant,
    entry: AeraConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up session switches for devices that support sessions."""
    coordinator = entry.runtime_data
    async_add_entities(
        AeraSessionSwitch(coordinator, dsn)
        for dsn, device in coordinator.data.devices.items()
        if device.has_session_feature
    )


class AeraSessionSwitch(AeraEntity, SwitchEntity):
    """Start or stop a timed session using the session duration number."""

    _attr_translation_key = "session"

    def __init__(self, coordinator: AeraCoordinator, dsn: str) -> None:
        """Initialize the switch."""
        super().__init__(coordinator, dsn, "session")

    @property
    def is_on(self) -> bool | None:
        """Return whether a session is running."""
        return self.device.session_active

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Start a session."""
        minutes = self.coordinator.session_minutes.get(self._dsn, DEFAULT_SESSION_MINUTES)
        await self.coordinator.async_command(
            self.coordinator.api.start_session(self.device, minutes)
        )
        self.device.update_properties({PROP_SESSION_STATE: 1})
        self.coordinator.async_update_listeners()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Stop the running session."""
        await self.coordinator.async_command(self.coordinator.api.stop_session(self.device))
        self.device.update_properties({PROP_SESSION_STATE: 0})
        self.coordinator.async_update_listeners()
