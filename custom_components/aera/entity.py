"""Base entity for the Aera for Home integration."""

from __future__ import annotations

from aera import AeraDevice

from homeassistant.helpers.device_registry import CONNECTION_NETWORK_MAC, DeviceInfo, format_mac
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import AeraCoordinator


class AeraEntity(CoordinatorEntity[AeraCoordinator]):
    """An entity belonging to one Aera diffuser."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: AeraCoordinator, dsn: str, key: str) -> None:
        """Initialize the entity."""
        super().__init__(coordinator)
        self._dsn = dsn
        self._attr_unique_id = f"{dsn}_{key}"
        device = self.device
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, dsn)},
            connections=(
                {(CONNECTION_NETWORK_MAC, format_mac(device.mac))} if device.mac else set()
            ),
            manufacturer="Aera",
            model=device.product_name or device.oem_model or None,
            model_id=device.oem_model or None,
            name=device.device_name,
            serial_number=dsn,
            sw_version=device.firmware_version or device.sw_version,
        )

    @property
    def device(self) -> AeraDevice:
        """Return the library device object (updated in place on every poll)."""
        return self.coordinator.data.devices[self._dsn]

    @property
    def available(self) -> bool:
        """Return whether the diffuser is reachable through the cloud."""
        return (
            super().available
            and self._dsn in self.coordinator.data.devices
            and self.device.is_online
        )
