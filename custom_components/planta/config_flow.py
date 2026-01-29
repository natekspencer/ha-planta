"""Config flow for Planta integration."""

from __future__ import annotations

import asyncio
from collections.abc import Mapping
import json
import logging
from typing import Any

from httpx import HTTPStatusError
import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_CODE, CONF_TOKEN
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import DOMAIN
from .pyplanta import Planta
from .pyplanta.exceptions import PlantaError, UnauthorizedError

_LOGGER = logging.getLogger(__name__)


STEP_USER_DATA_SCHEMA = vol.Schema({vol.Required(CONF_CODE): str})

CONF_PLANTA_URL = "planta_url"
PLANTA_URL = "https://getplanta.com/apps/manage"


class PlantaConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Planta."""

    VERSION = 1

    tokens: dict[str, str] | None = None

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

        if user_input is not None:
            if not (errors := await self.validate_client(user_input)):
                data = {
                    CONF_TOKEN: json.dumps(self.tokens),
                }
                if existing_entry := self.hass.config_entries.async_get_entry(
                    self.context.get("entry_id")
                ):
                    self.hass.config_entries.async_update_entry(
                        existing_entry, data=data
                    )
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
        except asyncio.TimeoutError:
            errors["base"] = "timeout_connect"
        except Exception as ex:  # pylint: disable=broad-except
            _LOGGER.error(ex)
            errors["base"] = "unknown"
        finally:
            await client.close()
        return errors
