"""Tests for the Planta options flow."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.planta.const import (
    CONF_APPLY_TO_EXISTING,
    CONF_ENABLE_ALL,
    CONF_ENABLED_SENSORS,
    DOMAIN,
)
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.helpers import entity_registry as er

from .test_sensor_defaults import sensor_entry

SECTIONS = ("plant", "scheduled", "last", "time_since_last")


def form_defaults(result: dict[str, Any]) -> dict[str, Any]:
    """Return the default values shown in the options form."""
    defaults = {}
    for key, value in result["data_schema"].schema.items():
        if str(key) in SECTIONS:
            (field,) = value.schema.schema
            defaults[str(key)] = field.default()
        else:
            defaults[str(key)] = key.default()
    return defaults


def user_input(
    *,
    plant: list[str] | None = None,
    scheduled: list[str] | None = None,
    last: list[str] | None = None,
    time_since_last: list[str] | None = None,
    enable_all: bool = False,
    apply_to_existing: bool = False,
) -> dict[str, Any]:
    """Return options form input."""
    return {
        CONF_ENABLE_ALL: enable_all,
        "plant": {"sensors": plant or []},
        "scheduled": {"sensors": scheduled or []},
        "last": {"sensors": last or []},
        "time_since_last": {"sensors": time_since_last or []},
        CONF_APPLY_TO_EXISTING: apply_to_existing,
    }


async def submit_options(
    hass: HomeAssistant, config_entry: MockConfigEntry, data: dict[str, Any]
) -> dict[str, Any]:
    """Open the options flow and submit it."""
    result = await hass.config_entries.options.async_init(config_entry.entry_id)
    result = await hass.config_entries.options.async_configure(result["flow_id"], data)
    await hass.async_block_till_done()
    return result


async def test_form_defaults(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    setup_integration: Callable[[], Any],
) -> None:
    """Test the form shows the default selection when no options are set."""
    await setup_integration()

    result = await hass.config_entries.options.async_init(config_entry.entry_id)

    assert result["type"] is FlowResultType.FORM
    assert form_defaults(result) == {
        CONF_ENABLE_ALL: False,
        "plant": [],
        "scheduled": ["cleaning", "fertilizing", "misting", "repotting", "watering"],
        "last": ["watering"],
        "time_since_last": [],
        CONF_APPLY_TO_EXISTING: False,
    }


async def test_save_options(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    setup_integration: Callable[[], Any],
) -> None:
    """Test the sections are saved as a single list of sensor keys."""
    await setup_integration()

    result = await submit_options(
        hass,
        config_entry,
        user_input(
            plant=["health"],
            scheduled=["watering"],
            time_since_last=["watering"],
        ),
    )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert config_entry.options == {
        CONF_ENABLE_ALL: False,
        CONF_ENABLED_SENSORS: [
            "health",
            "scheduled_watering",
            "time_since_last_watering",
        ],
    }

    result = await hass.config_entries.options.async_init(config_entry.entry_id)
    defaults = form_defaults(result)
    assert defaults["plant"] == ["health"]
    assert defaults["scheduled"] == ["watering"]
    assert defaults["last"] == []
    assert defaults["time_since_last"] == ["watering"]


@pytest.mark.parametrize(
    "options", [{CONF_ENABLE_ALL: True, CONF_ENABLED_SENSORS: ["pot_size"]}]
)
async def test_enable_all_keeps_selection(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    setup_integration: Callable[[], Any],
) -> None:
    """Test the section selection is kept while enable all is on."""
    await setup_integration()

    result = await hass.config_entries.options.async_init(config_entry.entry_id)
    defaults = form_defaults(result)

    assert defaults[CONF_ENABLE_ALL] is True
    assert defaults["plant"] == ["pot_size"]
    assert defaults["scheduled"] == []


async def test_apply_to_existing(
    hass: HomeAssistant,
    entity_registry: er.EntityRegistry,
    config_entry: MockConfigEntry,
    setup_integration: Callable[[], Any],
) -> None:
    """Test applying the selection to existing plants."""
    await setup_integration()
    health = sensor_entry(entity_registry, "plant1", "health").entity_id
    size = sensor_entry(entity_registry, "plant1", "size").entity_id
    scheduled_misting = sensor_entry(
        entity_registry, "plant1", "scheduled_misting"
    ).entity_id
    entity_registry.async_update_entity(size, disabled_by=er.RegistryEntryDisabler.USER)
    button = entity_registry.async_get_entity_id(
        "button", DOMAIN, "plant1-complete_misting"
    )

    await submit_options(
        hass,
        config_entry,
        user_input(
            plant=["health", "size"],
            scheduled=["watering"],
            apply_to_existing=True,
        ),
    )

    # Selected and disabled by the integration: enabled
    assert entity_registry.async_get(health).disabled_by is None
    # Selected, but disabled by the user: left alone
    assert entity_registry.async_get(size).disabled_by is er.RegistryEntryDisabler.USER
    # Not selected and enabled: disabled
    assert (
        entity_registry.async_get(scheduled_misting).disabled_by
        is er.RegistryEntryDisabler.INTEGRATION
    )
    # Other platforms are not affected
    assert entity_registry.async_get(button).disabled_by is None
    # Not saved as an option
    assert CONF_APPLY_TO_EXISTING not in config_entry.options


async def test_apply_to_existing_disables_manually_enabled(
    hass: HomeAssistant,
    entity_registry: er.EntityRegistry,
    config_entry: MockConfigEntry,
    setup_integration: Callable[[], Any],
) -> None:
    """Test applying to existing plants also disables manually enabled sensors.

    The entity registry doesn't record who enabled an entity, so this is
    expected and documented on the option.
    """
    await setup_integration()
    health = sensor_entry(entity_registry, "plant1", "health").entity_id
    entity_registry.async_update_entity(health, disabled_by=None)

    await submit_options(
        hass, config_entry, user_input(scheduled=["watering"], apply_to_existing=True)
    )

    assert (
        entity_registry.async_get(health).disabled_by
        is er.RegistryEntryDisabler.INTEGRATION
    )


async def test_without_apply_to_existing(
    hass: HomeAssistant,
    entity_registry: er.EntityRegistry,
    config_entry: MockConfigEntry,
    setup_integration: Callable[[], Any],
) -> None:
    """Test existing sensors are untouched when not applying to existing plants."""
    await setup_integration()
    before = {
        entry.entity_id: entry.disabled_by
        for entry in er.async_entries_for_config_entry(
            entity_registry, config_entry.entry_id
        )
    }

    await submit_options(hass, config_entry, user_input(plant=["health"]))

    assert {
        entry.entity_id: entry.disabled_by
        for entry in er.async_entries_for_config_entry(
            entity_registry, config_entry.entry_id
        )
    } == before


async def test_apply_enable_all_to_existing(
    hass: HomeAssistant,
    entity_registry: er.EntityRegistry,
    config_entry: MockConfigEntry,
    setup_integration: Callable[[], Any],
) -> None:
    """Test applying enable all enables every sensor not disabled by the user."""
    await setup_integration()
    size = sensor_entry(entity_registry, "plant1", "size").entity_id
    entity_registry.async_update_entity(size, disabled_by=er.RegistryEntryDisabler.USER)

    await submit_options(
        hass, config_entry, user_input(enable_all=True, apply_to_existing=True)
    )

    sensors = [
        entry
        for entry in er.async_entries_for_config_entry(
            entity_registry, config_entry.entry_id
        )
        if entry.domain == "sensor"
    ]
    assert {entry.entity_id for entry in sensors if entry.disabled} == {size}
