"""Select platform: active fragrance on Aera Mini.

Full-size diffusers read the fragrance from the cartridge chip, so it is only
exposed as a sensor there. The Mini has no chip; the app writes the fragrance
code after scanning the vial's QR code, which this select mirrors.
"""

from __future__ import annotations

from aera.const import PROP_SET_FRAGRANCE_IDENTIFIER

from homeassistant.components.select import SelectEntity
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import AeraConfigEntry, AeraCoordinator
from .entity import AeraEntity

PARALLEL_UPDATES = 1


async def async_setup_entry(
    hass: HomeAssistant,
    entry: AeraConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the fragrance select for Mini diffusers."""
    coordinator = entry.runtime_data
    async_add_entities(
        AeraFragranceSelect(coordinator, dsn)
        for dsn, device in coordinator.data.devices.items()
        if device.device_type.is_mini
    )


class AeraFragranceSelect(AeraEntity, SelectEntity):
    """Fragrance loaded in an Aera Mini."""

    _attr_translation_key = "fragrance"

    def __init__(self, coordinator: AeraCoordinator, dsn: str) -> None:
        """Initialize the select."""
        super().__init__(coordinator, dsn, "fragrance_select")

    def _codes_by_name(self) -> dict[str, str]:
        return {
            name: code
            for fragrance in self.coordinator.data.mini_fragrances
            if (name := fragrance["name"]) and (code := fragrance["code"])
        }

    @property
    def options(self) -> list[str]:
        """Return the Mini-compatible fragrance names."""
        return sorted(self._codes_by_name())

    @property
    def current_option(self) -> str | None:
        """Return the loaded fragrance, if it is a known Mini fragrance."""
        name = self.device.fragrance_name
        return name if name in self._codes_by_name() else None

    async def async_select_option(self, option: str) -> None:
        """Tell the diffuser which fragrance is loaded."""
        code = self._codes_by_name().get(option)
        if code is None:
            raise ServiceValidationError(f"Unknown fragrance: {option}")
        await self.coordinator.async_command(
            self.coordinator.api.set_property(self.device, PROP_SET_FRAGRANCE_IDENTIFIER, code)
        )
        # The fragrance name is resolved from the identifier during a poll.
        await self.coordinator.async_request_refresh()
