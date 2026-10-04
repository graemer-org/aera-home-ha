"""Fan platform: diffuser power and intensity as a percentage."""

from __future__ import annotations

import math
from typing import Any

from aera.const import PROP_INTENSITY_STATE, PROP_POWER_STATE

from homeassistant.components.fan import FanEntity, FanEntityFeature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.util.percentage import percentage_to_ranged_value, ranged_value_to_percentage

from .coordinator import AeraConfigEntry, AeraCoordinator
from .entity import AeraEntity

PARALLEL_UPDATES = 1


async def async_setup_entry(
    hass: HomeAssistant,
    entry: AeraConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the diffuser fan entities."""
    coordinator = entry.runtime_data
    async_add_entities(AeraFan(coordinator, dsn) for dsn in coordinator.data.devices)


class AeraFan(AeraEntity, FanEntity):
    """Diffuser on/off with intensity mapped onto 1..max_intensity."""

    _attr_name = None
    _attr_translation_key = "diffuser"
    _attr_supported_features = (
        FanEntityFeature.SET_SPEED | FanEntityFeature.TURN_ON | FanEntityFeature.TURN_OFF
    )

    def __init__(self, coordinator: AeraCoordinator, dsn: str) -> None:
        """Initialize the fan."""
        super().__init__(coordinator, dsn, "diffuser")

    @property
    def _speed_range(self) -> tuple[int, int]:
        return (1, self.device.max_intensity)

    @property
    def speed_count(self) -> int:
        """Return the number of intensity steps."""
        return self.device.max_intensity

    @property
    def is_on(self) -> bool | None:
        """Return whether the diffuser is running."""
        return self.device.is_power_on

    @property
    def percentage(self) -> int | None:
        """Return the current intensity as a percentage."""
        if not self.device.is_power_on:
            return 0
        intensity = self.device.intensity
        if intensity is None:
            return None
        return ranged_value_to_percentage(self._speed_range, intensity)

    async def async_turn_on(
        self,
        percentage: int | None = None,
        preset_mode: str | None = None,
        **kwargs: Any,
    ) -> None:
        """Turn the diffuser on, optionally at a given intensity."""
        if percentage == 0:
            await self.async_turn_off()
            return
        await self._async_set_power(True)
        if percentage is not None:
            await self._async_set_intensity(percentage)
        self.coordinator.async_update_listeners()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the diffuser off."""
        await self._async_set_power(False)
        self.coordinator.async_update_listeners()

    async def async_set_percentage(self, percentage: int) -> None:
        """Set intensity; 0 turns the diffuser off."""
        await self.async_turn_on(percentage=percentage)

    async def _async_set_power(self, on: bool) -> None:
        await self.coordinator.async_command(self.coordinator.api.set_power(self.device, on))
        # The device reports power_state on its next check-in; assume it follows.
        self.device.update_properties({PROP_POWER_STATE: 1 if on else 0})

    async def _async_set_intensity(self, percentage: int) -> None:
        level = math.ceil(percentage_to_ranged_value(self._speed_range, percentage))
        await self.coordinator.async_command(self.coordinator.api.set_intensity(self.device, level))
        self.device.update_properties({PROP_INTENSITY_STATE: level})
