"""Tests for common names on Planta image entities."""

from __future__ import annotations

from collections.abc import Callable
from copy import deepcopy
from typing import Any
from unittest.mock import MagicMock

import pytest

from custom_components.planta.const import DOMAIN
from homeassistant.core import HomeAssistant, State
from homeassistant.helpers import entity_registry as er

from . import MockConfigEntry


def image_state(hass: HomeAssistant, entity_registry: er.EntityRegistry) -> State:
    """Return the image state for the test plant."""
    entity_id = entity_registry.async_get_entity_id("image", DOMAIN, "plant1-image")
    assert entity_id is not None
    state = hass.states.get(entity_id)
    assert state is not None
    return state


async def test_common_name(
    hass: HomeAssistant,
    entity_registry: er.EntityRegistry,
    plants: list[dict[str, Any]],
    setup_integration: Callable[[], Any],
) -> None:
    """Expose the localized common name in the image state."""
    names = plants[0]["names"]
    names["custom"] = "Leafy"
    names["localizedName"] = "Monstera deliciosa común"
    await setup_integration()

    state = image_state(hass, entity_registry)
    assert state.attributes["common_name"] == "Monstera deliciosa común"


@pytest.mark.parametrize(
    "common_name",
    [
        "missing",
        None,
        "",
        "   ",
        [],
        {"name": "Monstera"},
        42,
        False,
    ],
)
async def test_invalid_common_name(
    hass: HomeAssistant,
    entity_registry: er.EntityRegistry,
    plants: list[dict[str, Any]],
    setup_integration: Callable[[], Any],
    common_name: Any,
) -> None:
    """Missing or malformed common names produce a null attribute."""
    if common_name == "missing":
        plants[0]["names"].pop("localizedName")
    else:
        plants[0]["names"]["localizedName"] = common_name
    await setup_integration()

    assert image_state(hass, entity_registry).attributes["common_name"] is None


async def test_common_name_updates(
    hass: HomeAssistant,
    entity_registry: er.EntityRegistry,
    config_entry: MockConfigEntry,
    mock_client: MagicMock,
    plants: list[dict[str, Any]],
    setup_integration: Callable[[], Any],
) -> None:
    """Full and individual plant refreshes update and clear the common name."""
    await setup_integration()
    entity_id = image_state(hass, entity_registry).entity_id
    updated = deepcopy(plants[0])
    updated["names"]["localizedName"] = "Swiss cheese plant"
    plants[0] = updated
    await config_entry.runtime_data.async_refresh()
    await hass.async_block_till_done()
    assert hass.states.get(entity_id).attributes["common_name"] == (
        "Swiss cheese plant"
    )

    for common_name, expected in (
        (None, None),
        ([], None),
        ("", None),
        ("Monstera", "Monstera"),
    ):
        mock_client.get_plant.return_value = {
            **updated,
            "names": {**updated["names"], "localizedName": common_name},
        }
        await config_entry.runtime_data.async_refresh_plant(updated["id"])
        await hass.async_block_till_done()
        assert hass.states.get(entity_id).attributes["common_name"] == expected


async def test_common_name_unrecorded(
    hass: HomeAssistant,
    entity_registry: er.EntityRegistry,
    setup_integration: Callable[[], Any],
) -> None:
    """Mark the common name as unrecorded while retaining it in live state."""
    await setup_integration()
    state = image_state(hass, entity_registry)
    assert state.attributes["common_name"] == "Monstera"
    assert "common_name" in state.state_info["unrecorded_attributes"]
