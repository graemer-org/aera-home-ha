"""Sensor platform: fragrance, refill level, session time, error code."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from aera import AeraDevice

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import PERCENTAGE, EntityCategory, UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import AeraConfigEntry, AeraCoordinator
from .entity import AeraEntity

PARALLEL_UPDATES = 0


@dataclass(frozen=True, kw_only=True)
class AeraSensorEntityDescription(SensorEntityDescription):
    """Describes an Aera sensor."""

    value_fn: Callable[[AeraDevice], str | int | None]
    exists_fn: Callable[[AeraDevice], bool] = lambda _: True


SENSORS: tuple[AeraSensorEntityDescription, ...] = (
    AeraSensorEntityDescription(
        key="fragrance",
        translation_key="fragrance",
        value_fn=lambda device: device.fragrance_name,
    ),
    AeraSensorEntityDescription(
        key="fragrance_remaining",
        translation_key="fragrance_remaining",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda device: device.fragrance_remaining,
    ),
    AeraSensorEntityDescription(
        key="session_time_left",
        translation_key="session_time_left",
        device_class=SensorDeviceClass.DURATION,
        native_unit_of_measurement=UnitOfTime.MINUTES,
        value_fn=lambda device: device.session_time_remaining,
        exists_fn=lambda device: device.has_session_feature,
    ),
    AeraSensorEntityDescription(
        key="error_condition",
        translation_key="error_condition",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda device: device.error_condition,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: AeraConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the sensors."""
    coordinator = entry.runtime_data
    async_add_entities(
        AeraSensor(coordinator, dsn, description)
        for dsn, device in coordinator.data.devices.items()
        for description in SENSORS
        if description.exists_fn(device)
    )


class AeraSensor(AeraEntity, SensorEntity):
    """A read-only diffuser value."""

    entity_description: AeraSensorEntityDescription

    def __init__(
        self,
        coordinator: AeraCoordinator,
        dsn: str,
        description: AeraSensorEntityDescription,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, dsn, description.key)
        self.entity_description = description

    @property
    def native_value(self) -> str | int | None:
        """Return the sensor value."""
        return self.entity_description.value_fn(self.device)
