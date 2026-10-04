"""Number platform: intensity and session duration."""

from __future__ import annotations

from aera.const import PROP_INTENSITY_STATE

from homeassistant.components.number import NumberEntity, NumberMode, RestoreNumber
from homeassistant.const import EntityCategory, UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import (
    DEFAULT_SESSION_MINUTES,
    MAX_SESSION_MINUTES,
    MIN_SESSION_MINUTES,
    SESSION_STEP_MINUTES,
)
from .coordinator import AeraConfigEntry, AeraCoordinator
from .entity import AeraEntity

PARALLEL_UPDATES = 1


async def async_setup_entry(
    hass: HomeAssistant,
    entry: AeraConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the number entities."""
    coordinator = entry.runtime_data
    entities: list[AeraEntity] = []
    for dsn, device in coordinator.data.devices.items():
        entities.append(AeraIntensityNumber(coordinator, dsn))
        if device.has_session_feature:
            entities.append(AeraSessionDurationNumber(coordinator, dsn))
    async_add_entities(entities)


class AeraIntensityNumber(AeraEntity, NumberEntity):
    """Manual intensity, 1..max_intensity for the device type."""

    _attr_translation_key = "intensity"
    _attr_native_min_value = 1
    _attr_native_step = 1
    _attr_mode = NumberMode.SLIDER

    def __init__(self, coordinator: AeraCoordinator, dsn: str) -> None:
        """Initialize the number."""
        super().__init__(coordinator, dsn, "intensity")

    @property
    def native_max_value(self) -> float:
        """Return the device type's maximum intensity."""
        return self.device.max_intensity

    @property
    def native_value(self) -> float | None:
        """Return the reported intensity."""
        return self.device.intensity

    async def async_set_native_value(self, value: float) -> None:
        """Set the intensity."""
        level = int(value)
        await self.coordinator.async_command(self.coordinator.api.set_intensity(self.device, level))
        self.device.update_properties({PROP_INTENSITY_STATE: level})
        self.coordinator.async_update_listeners()


class AeraSessionDurationNumber(AeraEntity, RestoreNumber):
    """Length used when the session switch starts a timed session (kept in HA only)."""

    _attr_translation_key = "session_duration"
    _attr_entity_category = EntityCategory.CONFIG
    _attr_native_min_value = MIN_SESSION_MINUTES
    _attr_native_max_value = MAX_SESSION_MINUTES
    _attr_native_step = SESSION_STEP_MINUTES
    _attr_native_unit_of_measurement = UnitOfTime.MINUTES
    _attr_mode = NumberMode.BOX

    def __init__(self, coordinator: AeraCoordinator, dsn: str) -> None:
        """Initialize the number."""
        super().__init__(coordinator, dsn, "session_duration")
        coordinator.session_minutes[dsn] = DEFAULT_SESSION_MINUTES

    async def async_added_to_hass(self) -> None:
        """Restore the last chosen duration."""
        await super().async_added_to_hass()
        last = await self.async_get_last_number_data()
        if last is not None and last.native_value is not None:
            self.coordinator.session_minutes[self._dsn] = int(last.native_value)

    @property
    def native_value(self) -> float:
        """Return the configured duration."""
        return self.coordinator.session_minutes[self._dsn]

    async def async_set_native_value(self, value: float) -> None:
        """Store a new duration."""
        self.coordinator.session_minutes[self._dsn] = int(value)
        self.async_write_ha_state()
