"""Config flow for YNAB integration."""

from __future__ import annotations

import asyncio
from typing import Any

import voluptuous as vol
from ynab import ApiClient, ApiException, Configuration, UserApi

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_ACCESS_TOKEN
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed

from .const import DOMAIN, LOGGER


async def validate_input(hass: HomeAssistant, data: dict[str, str]) -> dict[str, str]:
    """Validate the user input by connecting to the YNAB API."""
    configuration = Configuration(access_token=data[CONF_ACCESS_TOKEN])

    # Use the YNAB API client to validate the token
    try:
        with ApiClient(configuration) as api_client:
            user_api = UserApi(api_client)
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(None, user_api.get_user)
            user_id = response.data.user.id
    except ApiException as err:
        LOGGER.error("Error validating YNAB access token: %s", err)
        raise ConfigEntryAuthFailed("Invalid access token") from err

    LOGGER.info("YNAB user response: %s", response.data)
    LOGGER.info("YNAB user ID: %s", user_id)

    return {"title": "YNAB", "user_id": user_id}


class YnabConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for YNAB."""

    VERSION = 1

    LOGGER.info("YNAB config flow: async_step_user called")

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step."""
        errors = {}

        if user_input is not None:
            try:
                info = await validate_input(self.hass, user_input)
            except ConfigEntryAuthFailed:
                errors["base"] = "invalid_auth"
            except Exception:  # noqa: BLE001
                LOGGER.exception("Unexpected exception during YNAB config flow")
                errors["base"] = "unknown"
            else:
                # Check if an entry with the same access token already exists
                await self.async_set_unique_id(user_input[CONF_ACCESS_TOKEN])
                self._abort_if_unique_id_configured()

                return self.async_create_entry(
                    title=info["title"],
                    data={
                        CONF_ACCESS_TOKEN: user_input[CONF_ACCESS_TOKEN],
                        "user_id": info["user_id"],
                    },
                )

        data_schema = vol.Schema(
            {
                vol.Required(CONF_ACCESS_TOKEN): str,
            }
        )

        return self.async_show_form(
            step_id="user",
            data_schema=data_schema,
            errors=errors,
        )
