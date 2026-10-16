"""Fixtures for the Planta integration tests."""

from __future__ import annotations

from collections.abc import Callable, Generator
import json
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.planta.const import DOMAIN
from homeassistant.const import CONF_TOKEN
from homeassistant.core import HomeAssistant

ACTIONS = (
    "cleaning",
    "fertilizing",
    "misting",
    "progressUpdate",
    "repotting",
    "watering",
)


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations: None) -> None:
    """Enable loading the custom integration in all tests."""


def make_plant(plant_id: str, **overrides: Any) -> dict[str, Any]:
    """Return a plant payload with every sensor populated."""
    plant = {
        "id": f"user1:{plant_id}",
        "names": {
            "custom": f"Plant {plant_id}",
            "localizedName": "Monstera",
            "scientific": "Monstera deliciosa",
            "variety": None,
        },
        "site": {"name": "Living room"},
        "health": "good",
        "size": 40,
        "environment": {
            "pot": {"size": 20, "type": "potplastic", "soil": "allpurposepottingmix"}
        },
        "plantCare": {},
        "image": {},
        "actions": {
            action: {
                "next": {"date": "2026-10-20T00:00:00.000Z"},
                "completed": {"date": "2026-10-10T08:30:00.000Z", "type": "liquid"},
            }
            for action in ACTIONS
        },
    }
    plant.update(overrides)
    return plant


@pytest.fixture
def plants() -> list[dict[str, Any]]:
    """Return the plants reported by the mocked Planta API."""
    return [make_plant("plant1")]


@pytest.fixture
def mock_client(plants: list[dict[str, Any]]) -> Generator[MagicMock]:
    """Mock the Planta API client."""
    with patch("custom_components.planta.Planta", autospec=True) as client_class:
        client = client_class.return_value
        client.get_plants = AsyncMock(
            side_effect=lambda *args, **kwargs: {"plants": plants, "cursor": None}
        )
        yield client


@pytest.fixture
def options() -> dict[str, Any]:
    """Return the config entry options."""
    return {}


@pytest.fixture
def config_entry(hass: HomeAssistant, options: dict[str, Any]) -> MockConfigEntry:
    """Return a Planta config entry added to Home Assistant."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Planta",
        data={CONF_TOKEN: json.dumps({"accessToken": "token"})},
        options=options,
    )
    entry.add_to_hass(hass)
    return entry


@pytest.fixture
async def setup_integration(
    hass: HomeAssistant, config_entry: MockConfigEntry, mock_client: MagicMock
) -> Callable[[], Any]:
    """Return a function that sets up the integration."""

    async def _setup() -> None:
        assert await hass.config_entries.async_setup(config_entry.entry_id)
        await hass.async_block_till_done()

    return _setup
