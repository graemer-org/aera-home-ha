"""Tests for diagnostics."""

from __future__ import annotations

from pytest_homeassistant_custom_component.common import MockConfigEntry

from homeassistant.components.diagnostics import REDACTED
from homeassistant.core import HomeAssistant

from custom_components.aera.diagnostics import async_get_config_entry_diagnostics

from .conftest import FULL_DSN, PROPERTIES


async def test_diagnostics_dump_raw_properties(
    hass: HomeAssistant, setup_integration: MockConfigEntry
) -> None:
    """Diagnostics expose raw Ayla properties with secrets redacted."""
    # Arrange
    entry = setup_integration

    # Act
    result = await async_get_config_entry_diagnostics(hass, entry)

    # Assert
    assert result["entry"] == {"email": REDACTED, "password": REDACTED}
    device = result["devices"][FULL_DSN]
    assert device["mac"] == REDACTED
    assert device["device_type"] == "aera31"
    assert device["properties"] == PROPERTIES[FULL_DSN]
