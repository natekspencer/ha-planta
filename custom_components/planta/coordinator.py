"""Planta coordinator."""

from __future__ import annotations

from datetime import timedelta
import logging
from typing import Any

import async_timeout

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DOMAIN
from .pyplanta import Planta
from .pyplanta.exceptions import UnauthorizedError

_LOGGER = logging.getLogger(__name__)

UPDATE_INTERVAL = timedelta(minutes=5)

type PlantaConfigEntry = ConfigEntry[PlantaCoordinator]


class PlantaCoordinator(DataUpdateCoordinator[dict[str, dict[str, Any]]]):
    """Planta data update coordinator."""

    def __init__(
        self, hass: HomeAssistant, config_entry: PlantaConfigEntry, client: Planta
    ) -> None:
        """Initialize."""
        super().__init__(
            hass,
            _LOGGER,
            config_entry=config_entry,
            name=DOMAIN,
            update_interval=UPDATE_INTERVAL,
            always_update=False,
        )
        self.client = client
        self.previous_plants: set[str] = set()

        # Initialize previous_plants from the device registry so that
        # stale devices can be detected on the first update after restart.
        device_registry = dr.async_get(hass)
        for device in dr.async_entries_for_config_entry(
            device_registry, config_entry.entry_id
        ):
            for domain, identifier in device.identifiers:
                if domain == DOMAIN:
                    self.previous_plants.add(identifier)

    def get_plant(self, plant_id: str) -> dict[str, Any] | None:
        """Get a plant by it's id."""
        return self.data.get(plant_id, None) if self.data else None

    async def _async_update_data(self) -> dict[str, dict[str, Any]]:
        """Fetch the latest data."""
        try:
            async with async_timeout.timeout(30):
                data = await self.client.get_plants()
        except UnauthorizedError as err:
            raise ConfigEntryAuthFailed from err
        except TimeoutError as err:
            msg = "Timeout reading data from Planta"
            _LOGGER.exception(msg)
            raise UpdateFailed(msg) from err
        except Exception as ex:
            msg = "Couldn't read from Planta"
            _LOGGER.exception(msg)
            raise UpdateFailed(msg) from ex

        if data is None:
            raise ConfigEntryNotReady

        if not isinstance((raw_plants := data.get("plants")), list):
            raise UpdateFailed("Invalid plant list from Planta")

        plants = {plant["id"]: plant for plant in raw_plants}
        current_plants = {plant_id.split(":")[-1] for plant_id in plants}

        if data.get("cursor") is None and (
            stale_plants := self.previous_plants - current_plants
        ):
            device_registry = dr.async_get(self.hass)
            for device_id in stale_plants:
                # Home Assistant >= 2026.8
                if hasattr(device_registry, "async_get_device_by_identifier"):
                    device = device_registry.async_get_device_by_identifier(
                        (DOMAIN, device_id), self.config_entry.entry_id
                    )
                else:
                    device = device_registry.async_get_device(
                        identifiers={(DOMAIN, device_id)}
                    )
                if device:
                    device_registry.async_remove_device(device.id)
        self.previous_plants = current_plants

        return plants

    async def async_refresh_plant(self, plant_id: str) -> None:
        """Fetch the latest data for a plant."""
        if data := await self.client.get_plant(plant_id):
            self.data[plant_id] = data
            self.async_update_listeners()
