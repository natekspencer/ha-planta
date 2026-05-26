"""Planta image entity."""

from __future__ import annotations

from datetime import datetime

from homeassistant.components.image import ImageEntity, ImageEntityDescription
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .coordinator import PlantaConfigEntry, PlantaCoordinator
from .entity import PlantaEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: PlantaConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Planta images using config entry."""
    coordinator = entry.runtime_data
    known_plants: set[str] = set()

    def _check_plants() -> None:
        if new_plants := set(coordinator.data) - known_plants:
            known_plants.update(new_plants)
            async_add_entities(
                PlantaImageEntity(coordinator, IMAGE, plant_id)
                for plant_id in new_plants
            )

    _check_plants()
    entry.async_on_unload(coordinator.async_add_listener(_check_plants))


IMAGE = ImageEntityDescription(key="image", name=None)


class PlantaImageEntity(PlantaEntity, ImageEntity):
    """Planta image entity."""

    def __init__(
        self,
        coordinator: PlantaCoordinator,
        description: ImageEntityDescription,
        plant_id: str,
    ) -> None:
        """Initialize the entity."""
        super().__init__(coordinator, description, plant_id)
        ImageEntity.__init__(self, coordinator.hass)

    async def async_added_to_hass(self) -> None:
        self._handle_coordinator_update()
        await super().async_added_to_hass()

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        if not self.plant:
            return
        image = self.plant.get("image", {})
        if (url := image.get("url")) != self._attr_image_url:
            if last_updated := image.get("lastUpdated"):
                self._attr_image_last_updated = datetime.fromisoformat(last_updated)
            self._attr_image_url = url
            self._cached_image = None
        super()._handle_coordinator_update()
