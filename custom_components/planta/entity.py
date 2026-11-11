"""Planta entity."""

from __future__ import annotations

from typing import Any, NamedTuple

from stringcase import snakecase

from homeassistant.core import callback
from homeassistant.helpers.entity import DeviceInfo, EntityDescription
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    CUSTOM_TASK_PREFIX,
    DOMAIN,
    PRUNING_PREFIX,
    PRUNING_TECHNIQUES,
    TASK_LISTS,
)
from .coordinator import PlantaCoordinator


def get_plant_name(plant: dict) -> str:
    """Get plant name."""
    names = plant.get("names", {})
    return names.get("custom") or names.get("localizedName")


def is_task_action(action_type: str) -> bool:
    """Return if the action type is a pruning or custom task action."""
    return action_type.startswith((PRUNING_PREFIX, CUSTOM_TASK_PREFIX))


def get_plant_tasks(plant: dict[str, Any] | None) -> list[dict[str, Any]]:
    """Get the pruning and custom tasks of a plant."""
    actions = (plant or {}).get("actions") or {}
    return [
        task
        for task_list in TASK_LISTS
        if isinstance(tasks := actions.get(task_list), list)
        for task in tasks
        if isinstance(task, dict) and task.get("actionType")
    ]


def get_plant_action(
    plant: dict[str, Any] | None, action_type: str
) -> dict[str, Any] | None:
    """Get a plant action by its action type, including pruning and custom tasks."""
    if is_task_action(action_type):
        return next(
            (
                task
                for task in get_plant_tasks(plant)
                if task["actionType"] == action_type
            ),
            None,
        )
    action = ((plant or {}).get("actions") or {}).get(action_type)
    return action if isinstance(action, dict) else None


def get_task_name(task: dict[str, Any]) -> str:
    """Get the name of a custom task, falling back to its id."""
    return task.get("name") or task["actionType"].removeprefix(CUSTOM_TASK_PREFIX)


class TaskKey(NamedTuple):
    """Entity key and translation details of a pruning or custom task."""

    key: str
    translation_key: str
    translation_placeholders: dict[str, str] | None


def get_task_key(task: dict[str, Any]) -> TaskKey | None:
    """Get the entity key suffix of a pruning or custom task.

    Returns `None` for pruning techniques that aren't known yet.
    """
    action_type: str = task["actionType"]
    if action_type.startswith(PRUNING_PREFIX):
        if (
            technique := action_type.removeprefix(PRUNING_PREFIX)
        ) in PRUNING_TECHNIQUES:
            key = f"pruning_{snakecase(technique)}"
            return TaskKey(key, key, None)
        return None
    if action_type.startswith(CUSTOM_TASK_PREFIX):
        # "-" separates the plant id from the key in unique ids
        task_id = action_type.removeprefix(CUSTOM_TASK_PREFIX).replace("-", "_")
        return TaskKey(
            f"custom_task_{task_id}",
            "custom_task",
            {"task": get_task_name(task)},
        )
    return None


class PlantaEntity(CoordinatorEntity[PlantaCoordinator]):
    """Base class for Planta entities."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: PlantaCoordinator,
        description: EntityDescription,
        plant_id: str,
    ) -> None:
        """Construct a Planta entity."""
        super().__init__(coordinator)
        self.entity_description = description
        self.plant_id = plant_id

        # strip user id from plant_id
        plant_id = plant_id.split(":")[-1]

        self._attr_unique_id = f"{plant_id}-{description.key}"
        names = self.plant.get("names", {})
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, plant_id)},
            name=names.get("custom") or names.get("localizedName"),
            manufacturer="Planta",
            model=names.get("scientific")
            + (f" '{variety}'" if (variety := names.get("variety")) else ""),
            suggested_area=self.plant["site"]["name"],
        )

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self._update_task_name()
        super()._handle_coordinator_update()

    def _update_task_name(self) -> None:
        """Keep the name of a custom task entity in sync with the task."""
        field = getattr(self.entity_description, "field", None)
        if (
            field
            and field.startswith(CUSTOM_TASK_PREFIX)
            and (task := get_plant_action(self.plant, field))
            and (name := get_task_name(task))
            != self.translation_placeholders.get("task")
        ):
            self._attr_translation_placeholders = {"task": name}
            # The translated name is cached and only invalidated by setting
            # `_attr_name`, so invalidate it the same way Home Assistant does
            self.__dict__.pop("name", None)

    @property
    def plant(self) -> dict[str, Any] | None:
        """Get plant data."""
        return self.coordinator.get_plant(self.plant_id)

    @property
    def available(self) -> bool:
        """Return if entity is available.

        Pruning and custom task entities are unavailable once the task is removed.
        """
        if not super().available:
            return False
        field = getattr(self.entity_description, "field", None)
        if field and is_task_action(field):
            return get_plant_action(self.plant, field) is not None
        return True
