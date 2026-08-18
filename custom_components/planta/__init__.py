"""Support for Planta."""

from __future__ import annotations

import json
import logging

from homeassistant.const import CONF_TOKEN, Platform
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.device_registry import DeviceEntry

from .const import DOMAIN
from .coordinator import PlantaConfigEntry, PlantaCoordinator
from .pyplanta import Planta

_LOGGER = logging.getLogger(__name__)

PLATFORMS = [
    Platform.BUTTON,
    Platform.IMAGE,
    Platform.SENSOR,
    Platform.TODO,
]


async def async_setup_entry(hass: HomeAssistant, entry: PlantaConfigEntry) -> bool:
    """Set up Planta from a config entry."""

    @callback
    def async_save_tokens(tokens: dict[str, str]) -> None:
        """Save tokens to the config entry data."""
        _LOGGER.debug("Saving new tokens to HASS storage")
        hass.config_entries.async_update_entry(
            entry, data={**entry.data, CONF_TOKEN: json.dumps(tokens)}
        )

    if isinstance(tokens := entry.data[CONF_TOKEN], str):
        tokens = json.loads(tokens)

    client = Planta(
        session=async_get_clientsession(hass),
        tokens=tokens,
        refresh_tokens_callback=async_save_tokens,
    )
    coordinator = PlantaCoordinator(hass, entry, client)

    try:
        await coordinator.async_config_entry_first_refresh()
    except ConfigEntryAuthFailed:
        raise
    except Exception:
        msg = "Unexpected error setting up Planta entry"
        _LOGGER.exception(msg)

    if not coordinator.data:
        raise ConfigEntryNotReady

    entry.runtime_data = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: PlantaConfigEntry) -> bool:
    """Unload a config entry."""
    await entry.runtime_data.client.close()
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def async_remove_config_entry_device(
    hass: HomeAssistant, entry: PlantaConfigEntry, device_entry: DeviceEntry
) -> bool:
    """Remove a config entry from a device."""
    return not any(
        identifier
        for identifier in device_entry.identifiers
        if identifier[0] == DOMAIN
        for plant_id in entry.runtime_data.data
        if plant_id.split(":")[-1] == identifier[1]
    )
