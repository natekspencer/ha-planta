"""Tests for which Planta sensors are enabled by default."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any
from unittest.mock import MagicMock

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.planta.const import CONF_ENABLE_ALL, CONF_ENABLED_SENSORS, DOMAIN
from custom_components.planta.sensor import DEFAULT_ENABLED_SENSORS
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

from .conftest import make_plant

ALL_SENSOR_KEYS = {
    "health",
    "size",
    "growing_medium",
    "pot_size",
    "pot_type",
    "site",
    *(
        f"{prefix}_{action}"
        for prefix in ("scheduled", "last", "time_since_last")
        for action in (
            "cleaning",
            "fertilizing",
            "misting",
            "progress_update",
            "repotting",
            "watering",
        )
    ),
}


def sensor_entry(
    entity_registry: er.EntityRegistry, plant_id: str, key: str
) -> er.RegistryEntry:
    """Return the registry entry of a plant sensor."""
    entity_id = entity_registry.async_get_entity_id(
        "sensor", DOMAIN, f"{plant_id}-{key}"
    )
    assert entity_id, f"{plant_id}-{key} was not created"
    return entity_registry.async_get(entity_id)


def enabled_keys(entity_registry: er.EntityRegistry, plant_id: str) -> set[str]:
    """Return the sensor keys of a plant that are enabled."""
    return {
        key
        for key in ALL_SENSOR_KEYS
        if not sensor_entry(entity_registry, plant_id, key).disabled
    }


async def test_default_enabled_sensors(
    hass: HomeAssistant,
    entity_registry: er.EntityRegistry,
    setup_integration: Callable[[], Any],
) -> None:
    """Test only the recommended sensors are enabled without any options."""
    await setup_integration()

    assert enabled_keys(entity_registry, "plant1") == {
        "scheduled_cleaning",
        "scheduled_fertilizing",
        "scheduled_misting",
        "scheduled_repotting",
        "scheduled_watering",
        "last_watering",
    }
    assert set(DEFAULT_ENABLED_SENSORS) == enabled_keys(entity_registry, "plant1")
    assert (
        sensor_entry(entity_registry, "plant1", "health").disabled_by
        is er.RegistryEntryDisabler.INTEGRATION
    )


@pytest.mark.parametrize(
    "options", [{CONF_ENABLED_SENSORS: ["health", "pot_size", "last_misting"]}]
)
async def test_selected_sensors_enabled(
    hass: HomeAssistant,
    entity_registry: er.EntityRegistry,
    setup_integration: Callable[[], Any],
) -> None:
    """Test the selected sensor types are enabled and all others disabled."""
    await setup_integration()

    assert enabled_keys(entity_registry, "plant1") == {
        "health",
        "pot_size",
        "last_misting",
    }


@pytest.mark.parametrize(
    "options", [{CONF_ENABLE_ALL: True, CONF_ENABLED_SENSORS: ["health"]}]
)
async def test_enable_all(
    hass: HomeAssistant,
    entity_registry: er.EntityRegistry,
    setup_integration: Callable[[], Any],
) -> None:
    """Test enable all overrides the selection and enables every sensor type."""
    await setup_integration()

    assert enabled_keys(entity_registry, "plant1") == ALL_SENSOR_KEYS


@pytest.mark.parametrize(
    ("plants", "options"),
    [
        (
            [make_plant("plant1", health=None, site={"name": None})],
            {CONF_ENABLE_ALL: True},
        )
    ],
)
async def test_sensors_without_value_disabled(
    hass: HomeAssistant,
    entity_registry: er.EntityRegistry,
    setup_integration: Callable[[], Any],
) -> None:
    """Test sensors without a value start disabled even when selected."""
    await setup_integration()

    assert enabled_keys(entity_registry, "plant1") == ALL_SENSOR_KEYS - {
        "health",
        "site",
    }


async def test_unscheduled_action_sensors_not_created(
    hass: HomeAssistant,
    entity_registry: er.EntityRegistry,
    plants: list[dict[str, Any]],
    setup_integration: Callable[[], Any],
) -> None:
    """Test sensors of actions that aren't scheduled are not created."""
    plants[0]["actions"]["misting"]["next"] = None
    await setup_integration()

    for key in ("scheduled_misting", "last_misting", "time_since_last_misting"):
        assert not entity_registry.async_get_entity_id(
            "sensor", DOMAIN, f"plant1-{key}"
        )


async def test_option_change_applies_to_new_plants_only(
    hass: HomeAssistant,
    entity_registry: er.EntityRegistry,
    config_entry: MockConfigEntry,
    plants: list[dict[str, Any]],
    mock_client: MagicMock,
    setup_integration: Callable[[], Any],
) -> None:
    """Test changing the options affects new plants and keeps manual choices."""
    await setup_integration()

    # The user manually enables a sensor that is disabled by default
    entity_registry.async_update_entity(
        sensor_entry(entity_registry, "plant1", "health").entity_id,
        disabled_by=None,
    )

    hass.config_entries.async_update_entry(
        config_entry, options={CONF_ENABLED_SENSORS: ["pot_size"]}
    )
    await hass.config_entries.async_reload(config_entry.entry_id)
    await hass.async_block_till_done()

    # Existing plant keeps its sensors as they were, including the manual choice
    assert enabled_keys(entity_registry, "plant1") == set(DEFAULT_ENABLED_SENSORS) | {
        "health"
    }

    # A plant added afterwards follows the new options
    plants.append(make_plant("plant2"))
    await config_entry.runtime_data.async_refresh()
    await hass.async_block_till_done()

    assert enabled_keys(entity_registry, "plant2") == {"pot_size"}
