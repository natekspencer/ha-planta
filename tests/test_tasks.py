"""Tests for Planta pruning and custom tasks."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any
from unittest.mock import AsyncMock, MagicMock

from freezegun.api import FrozenDateTimeFactory
import pytest

from custom_components.planta.const import CONF_ENABLE_ALL, CONF_ENABLED_SENSORS, DOMAIN
from homeassistant.components.todo import TodoItemStatus
from homeassistant.const import STATE_UNAVAILABLE
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

from .conftest import make_plant

NEXT = "2026-10-20T00:00:00.000Z"
COMPLETED = "2026-10-10T08:30:00.000Z"


def pruning_task(technique: str, next_date: str | None = NEXT) -> dict[str, Any]:
    """Return a pruning task as reported by the Planta API."""
    return {
        "actionType": f"pruning:{technique}",
        "technique": technique,
        "next": {"date": next_date} if next_date else None,
        "completed": {"date": COMPLETED},
    }


def custom_task(task_id: str, name: str, next_date: str | None = NEXT) -> dict:
    """Return a custom task as reported by the Planta API."""
    return {
        "actionType": f"customTask:{task_id}",
        "name": name,
        "icon": "pruning",
        "iconUrl": None,
        "backgroundColor": None,
        "foregroundColor": None,
        "next": {"date": next_date} if next_date else None,
        "completed": None,
    }


def with_tasks(plant: dict[str, Any], pruning=(), custom=()) -> dict[str, Any]:
    """Add pruning and custom tasks to a plant."""
    plant["actions"]["pruning"] = list(pruning)
    plant["actions"]["customTasks"] = list(custom)
    return plant


def entity_id(
    entity_registry: er.EntityRegistry, key: str, domain: str = "sensor"
) -> str | None:
    """Return the entity id of a plant1 entity."""
    return entity_registry.async_get_entity_id(domain, DOMAIN, f"plant1-{key}")


@pytest.fixture
def plants() -> list[dict[str, Any]]:
    """Return a plant with a pruning and a custom task."""
    return [
        with_tasks(
            make_plant("plant1"),
            pruning=[pruning_task("deadHeadingPinching")],
            custom=[custom_task("abc-123", "Rotate pot")],
        )
    ]


@pytest.fixture
def mock_client(mock_client: MagicMock) -> MagicMock:
    """Mock the Planta API client actions."""
    mock_client.plant_action_complete = AsyncMock(return_value=True)
    mock_client.get_plant = AsyncMock(return_value=None)
    return mock_client


async def test_task_entities(
    hass: HomeAssistant,
    entity_registry: er.EntityRegistry,
    setup_integration: Callable[[], Any],
) -> None:
    """Test pruning and custom tasks get sensors and a button."""
    await setup_integration()

    for task in ("pruning_dead_heading_pinching", "custom_task_abc_123"):
        scheduled = entity_registry.async_get(
            entity_id(entity_registry, f"scheduled_{task}")
        )
        assert not scheduled.disabled
        assert hass.states.get(scheduled.entity_id).state == "2026-10-20"
        for key in (f"last_{task}", f"time_since_last_{task}"):
            assert entity_registry.async_get(entity_id(entity_registry, key)).disabled
        assert entity_id(entity_registry, f"complete_{task}", "button")

    state = hass.states.get(
        entity_id(entity_registry, "scheduled_pruning_dead_heading_pinching")
    )
    assert state.attributes["friendly_name"] == (
        "Plant plant1 Scheduled pruning (deadheading)"
    )
    state = hass.states.get(entity_id(entity_registry, "scheduled_custom_task_abc_123"))
    assert state.attributes["friendly_name"] == "Plant plant1 Scheduled Rotate pot"
    state = hass.states.get(
        entity_id(entity_registry, "complete_custom_task_abc_123", "button")
    )
    assert state.attributes["friendly_name"] == "Plant plant1 Complete Rotate pot"


@pytest.mark.parametrize(
    "plants",
    [
        [
            with_tasks(
                make_plant("plant1"),
                pruning=[
                    pruning_task("topping", next_date=None),
                    pruning_task("someNewTechnique"),
                ],
                custom=[custom_task("abc", "Rotate pot", next_date=None)],
            )
        ]
    ],
)
async def test_unscheduled_and_unknown_tasks_not_created(
    hass: HomeAssistant,
    entity_registry: er.EntityRegistry,
    setup_integration: Callable[[], Any],
) -> None:
    """Test entities aren't created for unscheduled tasks or unknown techniques."""
    await setup_integration()

    keys = {
        entry.unique_id.split("-", 1)[1]
        for entry in entity_registry.entities.values()
        if entry.platform == DOMAIN
    }
    assert not {key for key in keys if "pruning" in key or "custom_task" in key}


async def test_tasks_added_and_removed(
    hass: HomeAssistant,
    entity_registry: er.EntityRegistry,
    config_entry,
    plants: list[dict[str, Any]],
    setup_integration: Callable[[], Any],
) -> None:
    """Test tasks scheduled later are added and removed tasks become unavailable."""
    await setup_integration()

    plants[0] = with_tasks(make_plant("plant1"), pruning=[pruning_task("topping")])
    await config_entry.runtime_data.async_refresh()
    await hass.async_block_till_done()

    assert hass.states.get(entity_id(entity_registry, "scheduled_pruning_topping"))
    assert entity_id(entity_registry, "complete_pruning_topping", "button")
    for key, domain in (
        ("scheduled_pruning_dead_heading_pinching", "sensor"),
        ("complete_pruning_dead_heading_pinching", "button"),
    ):
        state = hass.states.get(entity_id(entity_registry, key, domain))
        assert state.state == STATE_UNAVAILABLE


async def test_custom_task_renamed(
    hass: HomeAssistant,
    entity_registry: er.EntityRegistry,
    config_entry,
    plants: list[dict[str, Any]],
    setup_integration: Callable[[], Any],
) -> None:
    """Test custom task entities follow a rename of the task."""
    await setup_integration()

    plants[0] = with_tasks(
        make_plant("plant1"), custom=[custom_task("abc-123", "Turn pot")]
    )
    await config_entry.runtime_data.async_refresh()
    await hass.async_block_till_done()

    for key, domain, name in (
        ("scheduled_custom_task_abc_123", "sensor", "Scheduled Turn pot"),
        ("complete_custom_task_abc_123", "button", "Complete Turn pot"),
    ):
        state = hass.states.get(entity_id(entity_registry, key, domain))
        assert state.attributes["friendly_name"] == f"Plant plant1 {name}"

    # An empty name falls back to the task id, as in the to-do lists
    plants[0] = with_tasks(make_plant("plant1"), custom=[custom_task("abc-123", "")])
    await config_entry.runtime_data.async_refresh()
    await hass.async_block_till_done()

    state = hass.states.get(entity_id(entity_registry, "scheduled_custom_task_abc_123"))
    assert state.attributes["friendly_name"] == "Plant plant1 Scheduled abc-123"


@pytest.mark.parametrize(
    "options", [{CONF_ENABLED_SENSORS: ["last_pruning", "time_since_last_custom_task"]}]
)
async def test_task_sensor_options(
    hass: HomeAssistant,
    entity_registry: er.EntityRegistry,
    setup_integration: Callable[[], Any],
) -> None:
    """Test task sensors follow the shared sensor type selected in the options."""
    await setup_integration()

    enabled = {
        key
        for task in ("pruning_dead_heading_pinching", "custom_task_abc_123")
        for prefix in ("scheduled", "last", "time_since_last")
        if not entity_registry.async_get(
            entity_id(entity_registry, key := f"{prefix}_{task}")
        ).disabled
    }
    # The custom task was never completed, so its time since last has no value
    assert enabled == {"last_pruning_dead_heading_pinching"}


@pytest.mark.parametrize("options", [{CONF_ENABLE_ALL: True}])
async def test_enable_all_task_sensors(
    hass: HomeAssistant,
    entity_registry: er.EntityRegistry,
    setup_integration: Callable[[], Any],
) -> None:
    """Test enable all enables task sensors that were never completed."""
    await setup_integration()

    for prefix in ("scheduled", "last", "time_since_last"):
        entry = entity_registry.async_get(
            entity_id(entity_registry, f"{prefix}_custom_task_abc_123")
        )
        assert not entry.disabled


async def test_complete_task_button(
    hass: HomeAssistant,
    entity_registry: er.EntityRegistry,
    mock_client: MagicMock,
    setup_integration: Callable[[], Any],
) -> None:
    """Test the complete button completes the task."""
    await setup_integration()

    await hass.services.async_call(
        "button",
        "press",
        {
            "entity_id": entity_id(
                entity_registry, "complete_pruning_dead_heading_pinching", "button"
            )
        },
        blocking=True,
    )
    mock_client.plant_action_complete.assert_awaited_once_with(
        "user1:plant1", "pruning:deadHeadingPinching"
    )


async def test_todo_tasks(
    hass: HomeAssistant,
    freezer: FrozenDateTimeFactory,
    mock_client: MagicMock,
    setup_integration: Callable[[], Any],
) -> None:
    """Test pruning and custom tasks are listed and can be completed as to-dos."""
    freezer.move_to("2026-10-20T19:00:00+00:00")
    await setup_integration()

    result = await hass.services.async_call(
        "todo",
        "get_items",
        {"entity_id": "todo.planta_today_s_tasks"},
        blocking=True,
        return_response=True,
    )
    summaries = {
        item["summary"] for item in result["todo.planta_today_s_tasks"]["items"]
    }
    assert {
        "Plant plant1: ✂️🌿 Prune (deadheading)",
        "Plant plant1: 📋 Rotate pot",
    } <= summaries

    for summary, action_type in (
        ("Plant plant1: ✂️🌿 Prune (deadheading)", "pruning:deadHeadingPinching"),
        ("Plant plant1: 📋 Rotate pot", "customTask:abc-123"),
    ):
        mock_client.plant_action_complete.reset_mock()
        await hass.services.async_call(
            "todo",
            "update_item",
            {
                "entity_id": "todo.planta_today_s_tasks",
                "item": summary,
                "status": TodoItemStatus.COMPLETED,
            },
            blocking=True,
        )
        mock_client.plant_action_complete.assert_awaited_once_with(
            "user1:plant1", action_type
        )
