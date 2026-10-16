"""Config flow for Planta integration."""

from __future__ import annotations

from collections.abc import Mapping
import json
import logging
from typing import Any

from httpx import HTTPStatusError
import voluptuous as vol

from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlowWithReload,
)
from homeassistant.const import CONF_CODE, CONF_TOKEN, Platform
from homeassistant.core import callback
from homeassistant.data_entry_flow import section
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import (
    BooleanSelector,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
)

from .const import CONF_APPLY_TO_EXISTING, CONF_ENABLE_ALL, CONF_ENABLED_SENSORS, DOMAIN
from .pyplanta import Planta
from .pyplanta.exceptions import PlantaError, UnauthorizedError
from .sensor import CARE_ACTIONS, PLANT_SENSOR_KEYS, get_enabled_sensors

_LOGGER = logging.getLogger(__name__)


STEP_USER_DATA_SCHEMA = vol.Schema({vol.Required(CONF_CODE): str})

CONF_PLANTA_URL = "planta_url"
PLANTA_URL = "https://getplanta.com/apps/manage"

CONF_SENSORS = "sensors"

# section id: (sensor key prefix, selectable values, selector translation key)
SENSOR_SECTIONS: dict[str, tuple[str, list[str], str]] = {
    "plant": ("", PLANT_SENSOR_KEYS, "plant_sensor"),
    "scheduled": ("scheduled_", CARE_ACTIONS, "care_action"),
    "last": ("last_", CARE_ACTIONS, "care_action"),
    "time_since_last": ("time_since_last_", CARE_ACTIONS, "care_action"),
}


class PlantaConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Planta."""

    VERSION = 1

    tokens: dict[str, str] | None = None

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> PlantaOptionsFlow:
        """Get the options flow for this handler."""
        return PlantaOptionsFlow()

    async def async_step_reauth(
        self, entry_data: Mapping[str, Any]
    ) -> ConfigFlowResult:
        """Handle a reauthorization flow request."""
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, str] | None = None
    ) -> ConfigFlowResult:
        """Handle user's reauth credentials."""
        return await self._async_step(
            step_id="reauth_confirm",
            schema=STEP_USER_DATA_SCHEMA,
            user_input=user_input,
        )

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step."""
        return await self._async_step("user", STEP_USER_DATA_SCHEMA, user_input)

    async def _async_step(
        self,
        step_id: str,
        schema: vol.Schema,
        user_input: dict[str, Any] | None = None,
        suggested_values: dict[str, Any] | None = None,
    ) -> ConfigFlowResult:
        """Handle step setup."""
        errors = {}

        if user_input is not None and not (
            errors := await self.validate_client(user_input)
        ):
            data = {
                CONF_TOKEN: json.dumps(self.tokens),
            }
            if existing_entry := self.hass.config_entries.async_get_entry(
                self.context.get("entry_id")
            ):
                self.hass.config_entries.async_update_entry(existing_entry, data=data)
                await self.hass.config_entries.async_reload(existing_entry.entry_id)
                return self.async_abort(reason="reconfigure_successful")

            return self.async_create_entry(title="Planta", data=data)

        return self.async_show_form(
            step_id=step_id,
            data_schema=self.add_suggested_values_to_schema(schema, suggested_values),
            errors=errors,
            description_placeholders={CONF_PLANTA_URL: PLANTA_URL},
        )

    async def validate_client(self, user_input: dict[str, Any]) -> dict[str, str]:
        """Validate client setup."""
        errors = {}
        try:
            client = Planta(session=async_get_clientsession(self.hass))
            await client.authorize(user_input[CONF_CODE])
            if not client.tokens:
                errors["base"] = "invalid_auth"
            self.tokens = client.tokens
        except UnauthorizedError:
            errors["base"] = "invalid_auth"
        except (PlantaError, HTTPStatusError) as err:
            errors["base"] = str(err)
        except TimeoutError:
            errors["base"] = "timeout_connect"
        except Exception as ex:  # pylint: disable=broad-except # noqa: BLE001
            _LOGGER.error(ex)
            errors["base"] = "unknown"
        finally:
            await client.close()
        return errors


class PlantaOptionsFlow(OptionsFlowWithReload):
    """Handle Planta options."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Manage the options."""
        if user_input is not None:
            enabled_sensors = [
                f"{prefix}{value}"
                for section_id, (prefix, _, _) in SENSOR_SECTIONS.items()
                for value in user_input[section_id][CONF_SENSORS]
            ]
            enable_all = user_input[CONF_ENABLE_ALL]
            if user_input.get(CONF_APPLY_TO_EXISTING):
                self._apply_to_existing(enable_all, set(enabled_sensors))
            return self.async_create_entry(
                data={
                    CONF_ENABLE_ALL: enable_all,
                    CONF_ENABLED_SENSORS: enabled_sensors,
                }
            )

        enabled_sensors = get_enabled_sensors(self.config_entry)
        schema = vol.Schema(
            {
                vol.Required(
                    CONF_ENABLE_ALL,
                    default=self.config_entry.options.get(CONF_ENABLE_ALL, False),
                ): BooleanSelector(),
                **{
                    vol.Required(section_id): section(
                        vol.Schema(
                            {
                                vol.Required(
                                    CONF_SENSORS,
                                    default=[
                                        value
                                        for value in values
                                        if f"{prefix}{value}" in enabled_sensors
                                    ],
                                ): SelectSelector(
                                    SelectSelectorConfig(
                                        options=values,
                                        multiple=True,
                                        mode=SelectSelectorMode.LIST,
                                        translation_key=translation_key,
                                    )
                                ),
                            }
                        ),
                        {"collapsed": True},
                    )
                    for section_id, (
                        prefix,
                        values,
                        translation_key,
                    ) in SENSOR_SECTIONS.items()
                },
                vol.Optional(CONF_APPLY_TO_EXISTING, default=False): BooleanSelector(),
            }
        )
        return self.async_show_form(step_id="init", data_schema=schema)

    def _apply_to_existing(self, enable_all: bool, enabled_sensors: set[str]) -> None:
        """Enable/disable existing sensors to match the selected sensor types.

        Entities disabled by the user are left untouched.
        """
        registry = er.async_get(self.hass)
        for entity in er.async_entries_for_config_entry(
            registry, self.config_entry.entry_id
        ):
            if entity.domain != Platform.SENSOR:
                continue
            key = entity.unique_id.rsplit("-", 1)[-1]
            if enable_all or key in enabled_sensors:
                if entity.disabled_by is er.RegistryEntryDisabler.INTEGRATION:
                    registry.async_update_entity(entity.entity_id, disabled_by=None)
            elif entity.disabled_by is None:
                registry.async_update_entity(
                    entity.entity_id,
                    disabled_by=er.RegistryEntryDisabler.INTEGRATION,
                )
