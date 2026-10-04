"""Tests for entity state and control."""

from __future__ import annotations

from aioresponses import aioresponses
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from homeassistant.components.fan import ATTR_PERCENTAGE, ATTR_PERCENTAGE_STEP
from homeassistant.components.number import ATTR_MAX, ATTR_VALUE
from homeassistant.components.select import ATTR_OPTION, ATTR_OPTIONS
from homeassistant.const import ATTR_ENTITY_ID
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import entity_registry as er

from .conftest import FULL_DSN, MINI_DSN, datapoint_url, sent_values


@pytest.mark.parametrize(
    ("entity_id", "expected"),
    [
        ("fan.living_room", "on"),
        ("fan.bedroom", "off"),
        ("number.living_room_intensity", "6"),
        ("number.bedroom_intensity", "3"),
        ("sensor.living_room_fragrance", "Wood Sage & Sea Salt"),
        ("sensor.living_room_fragrance_remaining", "70"),
        ("sensor.bedroom_fragrance", "Lavender"),
        ("sensor.bedroom_fragrance_remaining", "90"),
        ("sensor.living_room_error_code", "0"),
        ("binary_sensor.living_room_cartridge", "on"),
        ("binary_sensor.living_room_connectivity", "on"),
        ("binary_sensor.living_room_problem", "off"),
        ("select.bedroom_fragrance", "Lavender"),
        ("switch.living_room_session", "off"),
        ("number.living_room_session_duration", "60"),
    ],
)
async def test_initial_state(
    hass: HomeAssistant, setup_integration: MockConfigEntry, entity_id: str, expected: str
) -> None:
    """Entities reflect the polled properties."""
    # Arrange (setup_integration)

    # Act
    state = hass.states.get(entity_id)

    # Assert
    assert state is not None
    assert state.state == expected


async def test_unique_ids_use_dsn(
    hass: HomeAssistant, setup_integration: MockConfigEntry, entity_registry: er.EntityRegistry
) -> None:
    """Unique IDs are f"{dsn}_{key}"."""
    # Arrange (setup_integration)

    # Act
    entry = entity_registry.async_get("number.living_room_intensity")

    # Assert
    assert entry is not None
    assert entry.unique_id == f"{FULL_DSN}_intensity"


async def test_device_type_specific_entities(
    hass: HomeAssistant, setup_integration: MockConfigEntry
) -> None:
    """Fragrance select is Mini-only; cartridge sensor is full-size-only."""
    # Arrange (setup_integration)

    # Act
    full_select = hass.states.get("select.living_room_fragrance")
    mini_cartridge = hass.states.get("binary_sensor.bedroom_cartridge")

    # Assert
    assert full_select is None
    assert mini_cartridge is None


async def test_fan_percentage_maps_to_device_range(
    hass: HomeAssistant, setup_integration: MockConfigEntry
) -> None:
    """Full-size has 10 steps, Mini has 5."""
    # Arrange (setup_integration)

    # Act
    full = hass.states.get("fan.living_room")
    mini_intensity = hass.states.get("number.bedroom_intensity")

    # Assert
    assert full.attributes[ATTR_PERCENTAGE] == 60
    assert full.attributes[ATTR_PERCENTAGE_STEP] == 10
    assert mini_intensity.attributes[ATTR_MAX] == 5


async def test_fan_turn_on_with_percentage(
    hass: HomeAssistant, setup_integration: MockConfigEntry, healthy_cloud: aioresponses
) -> None:
    """Turning on at 50% on a Mini powers on and sets intensity 3 of 5."""
    # Arrange
    entity_id = "fan.bedroom"

    # Act
    await hass.services.async_call(
        "fan", "turn_on", {ATTR_ENTITY_ID: entity_id, ATTR_PERCENTAGE: 50}, blocking=True
    )

    # Assert
    assert sent_values(healthy_cloud, MINI_DSN, "set_power_state") == [1]
    assert sent_values(healthy_cloud, MINI_DSN, "set_intensity_manual") == [3]
    state = hass.states.get(entity_id)
    assert state.state == "on"
    assert state.attributes[ATTR_PERCENTAGE] == 60


async def test_fan_turn_off(
    hass: HomeAssistant, setup_integration: MockConfigEntry, healthy_cloud: aioresponses
) -> None:
    """Turning off writes set_power_state=0 and updates state optimistically."""
    # Arrange
    entity_id = "fan.living_room"

    # Act
    await hass.services.async_call("fan", "turn_off", {ATTR_ENTITY_ID: entity_id}, blocking=True)

    # Assert
    assert sent_values(healthy_cloud, FULL_DSN, "set_power_state") == [0]
    assert hass.states.get(entity_id).state == "off"


async def test_fan_set_percentage_zero_turns_off(
    hass: HomeAssistant, setup_integration: MockConfigEntry, healthy_cloud: aioresponses
) -> None:
    """0% is off, not intensity 0."""
    # Arrange
    entity_id = "fan.living_room"

    # Act
    await hass.services.async_call(
        "fan", "set_percentage", {ATTR_ENTITY_ID: entity_id, ATTR_PERCENTAGE: 0}, blocking=True
    )

    # Assert
    assert sent_values(healthy_cloud, FULL_DSN, "set_power_state") == [0]
    assert sent_values(healthy_cloud, FULL_DSN, "set_intensity_manual") == []


async def test_number_sets_intensity_and_updates_fan(
    hass: HomeAssistant, setup_integration: MockConfigEntry, healthy_cloud: aioresponses
) -> None:
    """Setting intensity writes set_intensity_manual and refreshes the fan too."""
    # Arrange
    entity_id = "number.living_room_intensity"

    # Act
    await hass.services.async_call(
        "number", "set_value", {ATTR_ENTITY_ID: entity_id, ATTR_VALUE: 9}, blocking=True
    )

    # Assert
    assert sent_values(healthy_cloud, FULL_DSN, "set_intensity_manual") == [9]
    assert hass.states.get(entity_id).state == "9"
    assert hass.states.get("fan.living_room").attributes[ATTR_PERCENTAGE] == 90


async def test_session_switch_uses_configured_duration(
    hass: HomeAssistant, setup_integration: MockConfigEntry, healthy_cloud: aioresponses
) -> None:
    """Starting a session sends the duration from the number entity."""
    # Arrange
    await hass.services.async_call(
        "number",
        "set_value",
        {ATTR_ENTITY_ID: "number.living_room_session_duration", ATTR_VALUE: 90},
        blocking=True,
    )

    # Act
    await hass.services.async_call(
        "switch", "turn_on", {ATTR_ENTITY_ID: "switch.living_room_session"}, blocking=True
    )
    await hass.services.async_call(
        "switch", "turn_off", {ATTR_ENTITY_ID: "switch.living_room_session"}, blocking=True
    )

    # Assert
    assert sent_values(healthy_cloud, FULL_DSN, "set_session_length") == [90, 0]
    assert hass.states.get("switch.living_room_session").state == "off"


async def test_mini_fragrance_select(
    hass: HomeAssistant, setup_integration: MockConfigEntry, healthy_cloud: aioresponses
) -> None:
    """Options come from Contentful; selecting writes the fragrance code."""
    # Arrange
    entity_id = "select.bedroom_fragrance"

    # Act
    await hass.services.async_call(
        "select",
        "select_option",
        {ATTR_ENTITY_ID: entity_id, ATTR_OPTION: "Fig Tree"},
        blocking=True,
    )

    # Assert
    assert hass.states.get(entity_id).attributes[ATTR_OPTIONS] == ["Fig Tree", "Lavender"]
    assert sent_values(healthy_cloud, MINI_DSN, "set_fragrance_identifier") == ["FIG"]


async def test_command_failure_raises(
    hass: HomeAssistant, setup_integration: MockConfigEntry, healthy_cloud: aioresponses
) -> None:
    """A cloud error surfaces to the caller and leaves state untouched."""
    # Arrange
    healthy_cloud.clear()
    healthy_cloud.post(datapoint_url(FULL_DSN, "set_power_state"), status=500)

    # Act
    with pytest.raises(HomeAssistantError):
        await hass.services.async_call(
            "fan", "turn_off", {ATTR_ENTITY_ID: "fan.living_room"}, blocking=True
        )

    # Assert
    assert hass.states.get("fan.living_room").state == "on"
