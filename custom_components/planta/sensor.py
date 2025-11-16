"""Planta sensor entity."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import logging
from typing import Any

from stringcase import snakecase

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import EntityCategory, UnitOfLength, UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import async_track_time_interval

from .coordinator import PlantaConfigEntry, PlantaCoordinator
from .entity import PlantaEntity

_LOGGER = logging.getLogger(__name__)

PLANT_HEALTH_LIST = [
    "notset",
    "poor",
    "fair",
    "sick",
    "good",
    "bad",
    "veryGood",
    "excellent",
]


def get_last_watering_completed(
    plant: dict[str, Any], time_since: bool = False
) -> float | None:
    """Get the last watering (or liquid fertilizing) completed."""
    actions = plant.get("actions", {})
    action_date = max(
        (
            datetime.fromisoformat(record["date"])
            for action_type in ("watering", "fertilizing")
            if (action := actions.get(action_type))
            and (record := action.get("completed"))
            and "date" in record
            and (action_type != "fertilizing" or record.get("type") == "liquid")
        ),
        default=None,
    )
    if time_since and action_date:
        return (datetime.now(timezone.utc) - action_date).total_seconds()
    return action_date


def get_plant_action_date(
    plant: dict[str, Any], action_type: str, completed: bool = False
) -> datetime | None:
    """Get plant action date."""
    action = plant["actions"].get(action_type, {})
    if record := action.get("completed" if completed else "next"):
        return datetime.fromisoformat(record["date"])
    return None


def time_since_last_completed(plant: dict[str, Any], action_type: str) -> float | None:
    """Get time since last completed action."""
    if action_date := get_plant_action_date(plant, action_type, True):
        return (datetime.now(timezone.utc) - action_date).total_seconds()
    return None


def custom_schedule(plant: dict[str, Any], schedule_type: str) -> dict[str, Any] | None:
    """Return custom schedule, if any."""
    if (schedule := plant["plantCare"].get(schedule_type, {})).get("enabled"):
        return {
            snakecase(key if key != "enabled" else "custom_schedule"): value
            for key, value in schedule.items()
        }
    return None


@dataclass(frozen=True, kw_only=True)
class PlantaSensorEntityDescription(SensorEntityDescription):
    """Planta sensor entity description."""

    field: str
    is_pot: bool = False
    value_fn: Callable[[dict[str, Any]], datetime | None] | None = None
    extra_state_attributes_fn: Callable[[dict[str, Any]], dict[str, Any]] | None = None


PLANT_DESCRIPTORS = (
    PlantaSensorEntityDescription(
        key="health",
        field="health",
        translation_key="health",
        icon="mdi:clipboard-pulse",
        device_class=SensorDeviceClass.ENUM,
        entity_category=EntityCategory.DIAGNOSTIC,
        options=PLANT_HEALTH_LIST,
    ),
    PlantaSensorEntityDescription(
        key="size",
        field="size",
        translation_key="size",
        device_class=SensorDeviceClass.DISTANCE,
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:arrow-up-down",
        native_unit_of_measurement=UnitOfLength.CENTIMETERS,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    PlantaSensorEntityDescription(
        key="growing_medium",
        field="soil",
        is_pot=True,
        translation_key="growing_medium",
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:pot",
    ),
    PlantaSensorEntityDescription(
        key="pot_size",
        field="size",
        is_pot=True,
        translation_key="pot_size",
        device_class=SensorDeviceClass.DISTANCE,
        entity_category=EntityCategory.DIAGNOSTIC,
        native_unit_of_measurement=UnitOfLength.CENTIMETERS,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    PlantaSensorEntityDescription(
        key="pot_type",
        field="type",
        is_pot=True,
        translation_key="pot_type",
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:pot-outline",
    ),
)
ACTION_DESCRIPTORS = (
    PlantaSensorEntityDescription(
        key="scheduled_cleaning",
        field="cleaning",
        translation_key="scheduled_cleaning",
        device_class=SensorDeviceClass.TIMESTAMP,
        value_fn=lambda plant: get_plant_action_date(plant, "cleaning"),
    ),
    PlantaSensorEntityDescription(
        key="last_cleaning",
        field="cleaning",
        translation_key="last_cleaning",
        device_class=SensorDeviceClass.TIMESTAMP,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda plant: get_plant_action_date(plant, "cleaning", True),
    ),
    PlantaSensorEntityDescription(
        key="time_since_last_cleaning",
        field="cleaning",
        translation_key="time_since_last_cleaning",
        device_class=SensorDeviceClass.DURATION,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        native_unit_of_measurement=UnitOfTime.SECONDS,
        suggested_unit_of_measurement=UnitOfTime.DAYS,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda plant: time_since_last_completed(plant, "cleaning"),
    ),
    PlantaSensorEntityDescription(
        key="scheduled_fertilizing",
        field="fertilizing",
        translation_key="scheduled_fertilizing",
        device_class=SensorDeviceClass.TIMESTAMP,
        value_fn=lambda plant: get_plant_action_date(plant, "fertilizing"),
        extra_state_attributes_fn=lambda plant: custom_schedule(
            plant, "customFertilizing"
        ),
    ),
    PlantaSensorEntityDescription(
        key="last_fertilizing",
        field="fertilizing",
        translation_key="last_fertilizing",
        device_class=SensorDeviceClass.TIMESTAMP,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda plant: get_plant_action_date(plant, "fertilizing", True),
    ),
    PlantaSensorEntityDescription(
        key="time_since_last_fertilizing",
        field="fertilizing",
        translation_key="time_since_last_fertilizing",
        device_class=SensorDeviceClass.DURATION,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        native_unit_of_measurement=UnitOfTime.SECONDS,
        suggested_unit_of_measurement=UnitOfTime.DAYS,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda plant: time_since_last_completed(plant, "fertilizing"),
    ),
    PlantaSensorEntityDescription(
        key="scheduled_misting",
        field="misting",
        translation_key="scheduled_misting",
        device_class=SensorDeviceClass.TIMESTAMP,
        value_fn=lambda plant: get_plant_action_date(plant, "misting"),
    ),
    PlantaSensorEntityDescription(
        key="last_misting",
        field="misting",
        translation_key="last_misting",
        device_class=SensorDeviceClass.TIMESTAMP,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda plant: get_plant_action_date(plant, "misting", True),
    ),
    PlantaSensorEntityDescription(
        key="time_since_last_misting",
        field="misting",
        translation_key="time_since_last_misting",
        device_class=SensorDeviceClass.DURATION,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        native_unit_of_measurement=UnitOfTime.SECONDS,
        suggested_unit_of_measurement=UnitOfTime.DAYS,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda plant: time_since_last_completed(plant, "misting"),
    ),
    PlantaSensorEntityDescription(
        key="scheduled_progress_update",
        field="progressUpdate",
        translation_key="scheduled_progress_update",
        device_class=SensorDeviceClass.TIMESTAMP,
        value_fn=lambda plant: get_plant_action_date(plant, "progressUpdate"),
    ),
    PlantaSensorEntityDescription(
        key="last_progress_update",
        field="progressUpdate",
        translation_key="last_progress_update",
        device_class=SensorDeviceClass.TIMESTAMP,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda plant: get_plant_action_date(plant, "progressUpdate", True),
    ),
    PlantaSensorEntityDescription(
        key="time_since_last_progress_update",
        field="progressUpdate",
        translation_key="time_since_last_progress_update",
        device_class=SensorDeviceClass.DURATION,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        native_unit_of_measurement=UnitOfTime.SECONDS,
        suggested_unit_of_measurement=UnitOfTime.DAYS,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda plant: time_since_last_completed(plant, "progressUpdate"),
    ),
    PlantaSensorEntityDescription(
        key="scheduled_repotting",
        field="repotting",
        translation_key="scheduled_repotting",
        device_class=SensorDeviceClass.TIMESTAMP,
        value_fn=lambda plant: get_plant_action_date(plant, "repotting"),
    ),
    PlantaSensorEntityDescription(
        key="last_repotting",
        field="repotting",
        translation_key="last_repotting",
        device_class=SensorDeviceClass.TIMESTAMP,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda plant: get_plant_action_date(plant, "repotting", True),
    ),
    PlantaSensorEntityDescription(
        key="time_since_last_repotting",
        field="repotting",
        translation_key="time_since_last_repotting",
        device_class=SensorDeviceClass.DURATION,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        native_unit_of_measurement=UnitOfTime.SECONDS,
        suggested_unit_of_measurement=UnitOfTime.DAYS,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda plant: time_since_last_completed(plant, "repotting"),
    ),
    PlantaSensorEntityDescription(
        key="scheduled_watering",
        field="watering",
        translation_key="scheduled_watering",
        device_class=SensorDeviceClass.TIMESTAMP,
        value_fn=lambda plant: get_plant_action_date(plant, "watering"),
        extra_state_attributes_fn=lambda plant: custom_schedule(
            plant, "customWatering"
        ),
    ),
    PlantaSensorEntityDescription(
        key="last_watering",
        field="watering",
        translation_key="last_watering",
        device_class=SensorDeviceClass.TIMESTAMP,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda plant: get_last_watering_completed(plant),
    ),
    PlantaSensorEntityDescription(
        key="time_since_last_watering",
        field="watering",
        translation_key="time_since_last_watering",
        device_class=SensorDeviceClass.DURATION,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        native_unit_of_measurement=UnitOfTime.SECONDS,
        suggested_unit_of_measurement=UnitOfTime.DAYS,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda plant: get_last_watering_completed(plant, True),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: PlantaConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Planta sensors using config entry."""
    coordinator: PlantaCoordinator = entry.runtime_data
    entities = [
        PlantaSensorEntity(coordinator, descriptor, plant_id)
        for plant_id in coordinator.data
        for descriptor in PLANT_DESCRIPTORS
    ]
    entities.extend(
        PlantaSensorEntity(coordinator, descriptor, plant_id)
        for plant_id, plant in coordinator.data.items()
        for descriptor in ACTION_DESCRIPTORS
        if plant["actions"][descriptor.field]["next"]
    )
    async_add_entities(entities)


class PlantaSensorEntity(PlantaEntity, SensorEntity):
    """Planta sensor entity."""

    entity_description: PlantaSensorEntityDescription

    @property
    def entity_registry_enabled_default(self) -> bool:
        """Return if the entity should be enabled when first added to the entity registry."""
        return (
            self.entity_description.entity_registry_enabled_default
            and self.native_value is not None
        )

    @property
    def extra_state_attributes(self):
        """Return entity specific state attributes."""
        if self.plant and (_fn := self.entity_description.extra_state_attributes_fn):
            return _fn(self.plant) or super().extra_state_attributes
        return super().extra_state_attributes

    @property
    def native_value(self) -> int | str | datetime | None:
        """Return the value reported by the sensor."""
        if not self.plant:
            return None
        if value_fn := self.entity_description.value_fn:
            return value_fn(self.plant)
        elif self.entity_description.is_pot:
            value = self.plant["environment"]["pot"][self.entity_description.field]
        else:
            value = self.plant[self.entity_description.field]
        if value is None:
            return value
        if self.device_class == SensorDeviceClass.TIMESTAMP:
            return datetime.fromisoformat(value)
        if isinstance(value, str):
            value = value.lower()
        if self.device_class == SensorDeviceClass.ENUM and value not in self.options:
            _LOGGER.warning("%s has an unknown value: %s", self.name, value)
            self.entity_description.options.append(value)
        return value

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        if self.device_class == SensorDeviceClass.DURATION:
            self.async_on_remove(
                async_track_time_interval(
                    self.hass, self._update_entity_state, timedelta(minutes=15)
                )
            )

    async def _update_entity_state(self, now: datetime | None = None) -> None:
        """Update the state of the entity."""
        self._handle_coordinator_update()
