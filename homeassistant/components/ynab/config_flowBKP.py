import asyncio
import logging

import voluptuous as vol
import ynab

from homeassistant.config_entries import (
    CONN_CLASS_CLOUD_POLL,
    ConfigFlow,
    ConfigFlowResult,
)
from homeassistant.const import CONF_ACCESS_TOKEN
from homeassistant.core import HomeAssistant

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


class YNABConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for YNAB."""

    # The schema version of the entries that it creates
    # Home Assistant will call your migrate method if the version changes
    VERSION = 1
    MINOR_VERSION = 1

    CONNECTION_CLASS = CONN_CLASS_CLOUD_POLL

    DATA_SCHEMA = vol.Schema({("access_token"): str})

    # def __init__(self) -> None:
    #     """Initialize the config flow."""
    #     self.budgets: dict[str, str] = {}

    async def validate_input(hass: HomeAssistant, data: dict[str, str]) -> None:
        """Validate the user input allows us to connect."""
        configuration = ynab.Configuration(access_token=data[CONF_ACCESS_TOKEN])
        api_client = ynab.ApiClient(configuration)
        user_api = ynab.UserApi(api_client)

        loop = asyncio.get_event_loop()

        await loop.run_in_executor(None, user_api.get_user)

    async def async_step_user(self, user_input=None) -> ConfigFlowResult:
        """Handle the initial step."""
        # budgets = await self.async_get_budgets()

        _LOGGER.debug("User input: %s", user_input)

        if user_input is not None:
            pass  # TODO: process info

        return self.async_show_form(
            step_id="user", data_schema=self._get_config_schema()
        )

    #     errors = {}
    #     if user_input is not None:
    #         try:
    #             info = await validate_input(self.hass, user_input)

    def _get_config_schema(self):
        return vol.Schema({vol.Required("access_token"): str})
