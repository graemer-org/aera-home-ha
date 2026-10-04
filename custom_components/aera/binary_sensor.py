"""Binary sensor platform: connectivity, cartridge, error state."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from aera import AeraDevice

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import AeraConfigEntry, AeraCoordinator
from .entity import AeraEntity

PARALLEL_UPDATES = 0


@dataclass(frozen=True, kw_only=True)
class AeraBinarySensorEntityDescription(BinarySensorEntityDescription):
    """Describes an Aera binary sensor."""

    value_fn: Callable[[AeraDevice], bool | None]
    exists_fn: Callable[[AeraDevice], bool] = lambda _: True
    # Connectivity must keep reporting while the device itself is offline.
    requires_online: bool = True


BINARY_SENSORS: tuple[AeraBinarySensorEntityDescription, ...] = (
    AeraBinarySensorEntityDescription(
        key="online",
        device_class=BinarySensorDeviceClass.CONNECTIVITY,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda device: device.is_online,
        requires_online=False,
    ),
    AeraBinarySensorEntityDescription(
        key="cartridge_present",
        translation_key="cartridge_present",
        value_fn=lambda device: device.is_cartridge_present,
        exists_fn=lambda device: device.device_type.is_full_size,
    ),
    AeraBinarySensorEntityDescription(
        key="error",
        device_class=BinarySensorDeviceClass.PROBLEM,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda device: None if device.error_condition is None else device.has_error,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: AeraConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the binary sensors."""
    coordinator = entry.runtime_data
    async_add_entities(
        AeraBinarySensor(coordinator, dsn, description)
        for dsn, device in coordinator.data.devices.items()
        for description in BINARY_SENSORS
        if description.exists_fn(device)
    )


class AeraBinarySensor(AeraEntity, BinarySensorEntity):
    """A boolean diffuser value."""

    entity_description: AeraBinarySensorEntityDescription

    def __init__(
        self,
        coordinator: AeraCoordinator,
        dsn: str,
        description: AeraBinarySensorEntityDescription,
    ) -> None:
        """Initialize the binary sensor."""
        super().__init__(coordinator, dsn, description.key)
        self.entity_description = description

    @property
    def available(self) -> bool:
        """Return availability; connectivity stays available while offline."""
        if self.entity_description.requires_online:
            return super().available
        return self.coordinator.last_update_success and self._dsn in self.coordinator.data.devices

    @property
    def is_on(self) -> bool | None:
        """Return the sensor state."""
        return self.entity_description.value_fn(self.device)
