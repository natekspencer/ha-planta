"""Planta to-do list entity."""

from __future__ import annotations

from collections.abc import Iterator
from datetime import date, timedelta
import json
import logging
from typing import Final, override

from homeassistant.components.todo import (
    TodoItem,
    TodoItemStatus,
    TodoListEntity,
    TodoListEntityFeature,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity import EntityDescription
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
import homeassistant.util.dt as dt_util

from . import PlantaConfigEntry
from .const import CUSTOM_TASK_PREFIX, DOMAIN, PRUNING_PREFIX
from .coordinator import PlantaCoordinator
from .entity import get_plant_name, get_plant_tasks, get_task_name, is_task_action

_LOGGER = logging.getLogger(__name__)

ACTION_TYPE_MAP: Final[dict[str, str]] = {
    "cleaning": "✨🍃 Clean",
    "fertilizing": "🌱💩 Fertilize",
    "misting": "💦🌿 Mist",
    "progressUpdate": "📸🌸 Progress update",
    "repotting": "🪴🔄 Repot",
    "watering": "🪴💧 Water",
}
ALLOWED_ACTIONS: Final[set[str]] = {"cleaning", "fertilizing", "misting", "watering"}
PRUNING_TECHNIQUE_MAP: Final[dict[str, str]] = {
    "deadHeadingPinching": "deadheading",
    "deadWooding": "deadwooding",
    "cutBackOneThird": "cut back by a third",
    "removeSuckersPinching": "remove suckers",
    "removeFlowersPinching": "remove flowers",
    "lollipopping": "lollipopping",
    "topping": "topping",
    "thinning": "thinning",
}

TODO_LISTS = ("today", "upcoming")


def _is_allowed_action(action_type: str) -> bool:
    """Return if the action can be completed through the API."""
    return action_type in ALLOWED_ACTIONS or is_task_action(action_type)


def _action_name(action_type: str, details: dict | None = None) -> str:
    """Get the display name of an action."""
    if action_type.startswith(PRUNING_PREFIX):
        technique = action_type.removeprefix(PRUNING_PREFIX)
        return f"✂️🌿 Prune ({PRUNING_TECHNIQUE_MAP.get(technique, technique)})"
    if action_type.startswith(CUSTOM_TASK_PREFIX):
        return f"📋 {get_task_name(details or {'actionType': action_type})}"
    return ACTION_TYPE_MAP.get(action_type, action_type.title())


def _plant_actions(actions: dict) -> Iterator[tuple[str, dict]]:
    """Yield the action type and details of each action, including tasks."""
    for action_type, details in actions.items():
        if isinstance(details, dict):
            yield action_type, details
    for task in get_plant_tasks({"actions": actions}):
        yield task["actionType"], task


def _today() -> date:
    """Return today's date."""
    return dt_util.now().date()


def _todo_items(
    coordinator: PlantaCoordinator,
) -> Iterator[tuple[date, TodoItem]]:
    """Yield to-do items."""
    today = _today()

    for plant_id, plant in coordinator.data.items():
        if not (actions := plant.get("actions")) or not isinstance(actions, dict):
            continue

        plant_name = get_plant_name(plant)
        site_name = plant.get("site", {}).get("name")

        for action_type, details in _plant_actions(actions):
            action_name = _action_name(action_type, details)
            if not _is_allowed_action(action_type):
                action_name += " (app only)"
            summary = f"{plant_name}: {action_name}"
            uid = json.dumps((plant_id, action_type))
            completed = None

            if (
                (completed_str := (details.get("completed") or {}).get("date"))
                and (completed := dt_util.parse_datetime(completed_str))
                and completed.astimezone(dt_util.DEFAULT_TIME_ZONE).date() == today
            ):
                yield (
                    today,
                    TodoItem(
                        summary=summary,
                        uid=uid,
                        status=TodoItemStatus.COMPLETED,
                        due=today,
                        description=site_name,
                        completed=completed,
                    ),
                )

            if (
                (next_action := details.get("next") or {})
                and (date_str := next_action.get("date"))
                and (next_due := dt_util.parse_date(date_str[:10]))
                and next_due is not None
            ):
                yield (
                    next_due,
                    TodoItem(
                        summary=summary,
                        uid=uid,
                        status=TodoItemStatus.NEEDS_ACTION,
                        due=next_due,
                        description=site_name,
                        completed=completed,
                    ),
                )


def _get_todo_items(
    coordinator: PlantaCoordinator,
    *,
    start_days: int | None = None,
    end_days: int | None = None,
) -> Iterator[TodoItem]:
    """Yield to-do items whose date falls within the window."""
    today = _today()
    lo = today + timedelta(days=start_days) if start_days is not None else None
    hi = today + timedelta(days=end_days) if end_days is not None else None

    for window_date, item in _todo_items(coordinator):
        if (lo is None or window_date >= lo) and (hi is None or window_date <= hi):
            yield item


async def async_setup_entry(
    hass: HomeAssistant,
    entry: PlantaConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up Planta todo using config entry."""
    async_add_entities(
        PlantaTodoListEntity(entry.runtime_data, key) for key in TODO_LISTS
    )


class PlantaTodoListEntity(CoordinatorEntity[PlantaCoordinator], TodoListEntity):
    """Planta to-do list entity."""

    _attr_has_entity_name = True
    _attr_supported_features = TodoListEntityFeature.UPDATE_TODO_ITEM

    def __init__(self, coordinator: PlantaCoordinator, key: str) -> None:
        """Construct a Planta to-do list entity."""
        super().__init__(coordinator)
        self.entity_description = EntityDescription(key=key, translation_key=key)

        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"{coordinator.config_entry.entry_id}_service")},
            manufacturer="Planta",
            entry_type=DeviceEntryType.SERVICE,
        )
        self._attr_unique_id = f"{coordinator.config_entry.entry_id}-{key}"

        self._today: date | None = None

    @property
    @override
    def todo_items(self) -> list[TodoItem] | None:
        """Return the To-do items in the To-do list."""
        if self._today != _today():
            self._handle_coordinator_update()
        return self._attr_todo_items

    @override
    async def async_update_todo_item(self, item: TodoItem) -> None:
        """Update a To-do item."""
        if not item.status == TodoItemStatus.COMPLETED:
            raise ServiceValidationError(
                translation_domain=DOMAIN, translation_key="complete_only"
            )
        plant_id, action_type = json.loads(item.uid)
        if not _is_allowed_action(action_type):
            action_name = _action_name(action_type)
            raise ServiceValidationError(
                translation_domain=DOMAIN,
                translation_key="invalid_action",
                translation_placeholders={"action": action_name},
            )
        await self.coordinator.client.plant_action_complete(plant_id, action_type)
        await self.coordinator.async_refresh_plant(plant_id)

    @callback
    @override
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        start, end = (None, 0) if self.entity_description.key == "today" else (1, 30)
        items = list(_get_todo_items(self.coordinator, start_days=start, end_days=end))
        items = sorted(items, key=lambda t: (t.due, t.description or "", t.summary))
        self._attr_todo_items = items
        self._today = _today()
        super()._handle_coordinator_update()

    @override
    async def async_added_to_hass(self) -> None:
        """When entity is added to hass."""
        self._handle_coordinator_update()
        await super().async_added_to_hass()
