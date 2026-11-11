"""Planta button entity."""

from __future__ import annotations

from dataclasses import dataclass
import logging
from typing import Any

from homeassistant.components.button import ButtonEntity, ButtonEntityDescription
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .coordinator import PlantaConfigEntry
from .entity import PlantaEntity, get_plant_action, get_plant_tasks, get_task_key

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: PlantaConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Planta buttons using config entry."""
    coordinator = entry.runtime_data
    known_plants: set[str] = set()
    known_tasks: set[tuple[str, str]] = set()

    def _check_plants() -> None:
        entities: list[PlantaButtonEntity] = []
        if new_plants := set(coordinator.data) - known_plants:
            known_plants.update(new_plants)
            entities.extend(
                PlantaButtonEntity(coordinator, description, plant_id)
                for plant_id in new_plants
                for description in BUTTONS
            )
        # Pruning and custom tasks come and go, so check every plant on each update
        for plant_id, plant in coordinator.data.items():
            for task in get_plant_tasks(plant):
                if (plant_id, task["actionType"]) in known_tasks or not task.get(
                    "next"
                ):
                    continue
                known_tasks.add((plant_id, task["actionType"]))
                if description := task_button_description(task):
                    entities.append(
                        PlantaButtonEntity(coordinator, description, plant_id)
                    )
        if entities:
            async_add_entities(entities)

    _check_plants()
    entry.async_on_unload(coordinator.async_add_listener(_check_plants))


@dataclass(frozen=True, kw_only=True)
class PlantaButtonEntityDescription(ButtonEntityDescription):
    """Planta button entity description."""

    field: str


BUTTONS = (
    PlantaButtonEntityDescription(
        key="complete_cleaning",
        translation_key="complete_cleaning",
        field="cleaning",
    ),
    PlantaButtonEntityDescription(
        key="complete_fertilizing",
        translation_key="complete_fertilizing",
        field="fertilizing",
    ),
    PlantaButtonEntityDescription(
        key="complete_misting",
        translation_key="complete_misting",
        field="misting",
    ),
    PlantaButtonEntityDescription(
        key="complete_watering",
        translation_key="complete_watering",
        field="watering",
    ),
)


def task_button_description(
    task: dict[str, Any],
) -> PlantaButtonEntityDescription | None:
    """Get the button description of a pruning or custom task."""
    if not (task_key := get_task_key(task)):
        return None
    return PlantaButtonEntityDescription(
        key=f"complete_{task_key.key}",
        translation_key=f"complete_{task_key.translation_key}",
        translation_placeholders=task_key.translation_placeholders,
        field=task["actionType"],
    )


class PlantaButtonEntity(PlantaEntity, ButtonEntity):
    """Planta button entity."""

    entity_description: PlantaButtonEntityDescription

    @property
    def entity_registry_enabled_default(self) -> bool:
        """Return if the entity should be enabled when first added to the entity registry."""
        action = get_plant_action(self.plant, self.entity_description.field) or {}
        return action.get("next") is not None

    async def async_press(self) -> None:
        """Handle the button press."""
        if not self.plant_id or not (action := self.entity_description.field):
            raise ServiceValidationError(
                f"{self.name} cannot be performed on {self.device_entry.name}"
            )

        await self.coordinator.client.plant_action_complete(self.plant_id, action)
        await self.coordinator.async_refresh_plant(self.plant_id)
