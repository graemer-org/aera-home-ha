"""Tests for the Aera config flow."""

from __future__ import annotations

from aioresponses import aioresponses
from pytest_homeassistant_custom_component.common import MockConfigEntry

from homeassistant.config_entries import SOURCE_USER
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

from custom_components.aera.const import DOMAIN

from .conftest import EMAIL, PASSWORD, SIGN_IN_URL, TOKENS, register_cloud


async def test_user_flow_creates_entry(hass: HomeAssistant, cloud: aioresponses) -> None:
    """Valid credentials create an entry keyed by email."""
    # Arrange
    cloud.post(SIGN_IN_URL, payload=TOKENS)
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})

    # Act
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_EMAIL: f" {EMAIL.upper()} ", CONF_PASSWORD: PASSWORD}
    )

    # Assert
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == EMAIL.upper()
    assert result["data"] == {CONF_EMAIL: EMAIL.upper(), CONF_PASSWORD: PASSWORD}
    assert result["result"].unique_id == EMAIL


async def test_user_flow_invalid_auth_then_recovers(
    hass: HomeAssistant, cloud: aioresponses
) -> None:
    """A 401 shows invalid_auth and the form can be resubmitted."""
    # Arrange
    cloud.post(SIGN_IN_URL, status=401)
    cloud.post(SIGN_IN_URL, payload=TOKENS)
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})

    # Act
    failed = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_EMAIL: EMAIL, CONF_PASSWORD: "wrong"}
    )
    succeeded = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_EMAIL: EMAIL, CONF_PASSWORD: PASSWORD}
    )

    # Assert
    assert failed["type"] is FlowResultType.FORM
    assert failed["errors"] == {"base": "invalid_auth"}
    assert succeeded["type"] is FlowResultType.CREATE_ENTRY


async def test_user_flow_cannot_connect(hass: HomeAssistant, cloud: aioresponses) -> None:
    """A transport error shows cannot_connect."""
    # Arrange
    cloud.post(SIGN_IN_URL, exception=TimeoutError())
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})

    # Act
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_EMAIL: EMAIL, CONF_PASSWORD: PASSWORD}
    )

    # Assert
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "cannot_connect"}


async def test_user_flow_aborts_for_existing_account(
    hass: HomeAssistant, config_entry: MockConfigEntry, cloud: aioresponses
) -> None:
    """The same account can only be added once."""
    # Arrange
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})

    # Act
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_EMAIL: EMAIL, CONF_PASSWORD: PASSWORD}
    )

    # Assert
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"


async def test_reauth_updates_password(
    hass: HomeAssistant, config_entry: MockConfigEntry, cloud: aioresponses
) -> None:
    """Reauth stores the new password and reloads the entry."""
    # Arrange
    register_cloud(cloud)
    result = await config_entry.start_reauth_flow(hass)

    # Act
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_PASSWORD: "new-password"}
    )
    await hass.async_block_till_done()

    # Assert
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reauth_successful"
    assert config_entry.data[CONF_PASSWORD] == "new-password"
