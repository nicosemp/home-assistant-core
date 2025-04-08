"""Config flow for YNAB integration."""

from __future__ import annotations

import asyncio
import functools
from typing import Any

import voluptuous as vol
from ynab import ApiClient, ApiException, BudgetsApi, Configuration, UserApi

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_ACCESS_TOKEN
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers import config_validation as cv

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

    return {"title": "YNAB", "user_id": user_id}


# TODO: Should this fetch be done in the coordinator?
async def fetch_budgets(hass: HomeAssistant, access_token: str) -> list[dict[str, str]]:
    """Fetch the list of budgets from the YNAB API."""
    configuration = Configuration(access_token=access_token)

    try:
        with ApiClient(configuration) as api_client:
            budgets_api = BudgetsApi(api_client)
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None, functools.partial(budgets_api.get_budgets, include_accounts=True)
            )
            budgets = response.data.budgets
            return [
                {
                    "id": budget.id,
                    "name": budget.name,
                    "currency": budget.currency_format.iso_code,
                    "accounts": [
                        {
                            "id": account.id,
                            "name": account.name,
                            "balance": account.balance,
                            "deleted": account.deleted,
                            "closed": account.closed,
                        }
                        for account in budget.accounts
                        if account.deleted is False and account.closed is False
                    ],
                }
                for budget in budgets
            ]
    except ApiException as err:
        LOGGER.error("Error fetching budgets from YNAB API: %s", err)
        raise ConfigEntryAuthFailed("Failed to fetch budgets") from err


class YnabConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for YNAB."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the config flow."""
        self.access_token: str | None = None
        self.user_id: str | None = None
        self.budgets: list[dict[str, str]] = []

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step."""
        errors = {}

        if user_input is not None:
            try:
                info = await validate_input(self.hass, user_input)
                self.access_token = user_input[CONF_ACCESS_TOKEN]
                self.user_id = info["user_id"]
            except ConfigEntryAuthFailed:
                errors["base"] = "invalid_auth"
            except Exception:  # noqa: BLE001
                LOGGER.exception("Unexpected exception during YNAB config flow")
                errors["base"] = "unknown"
            else:
                # Check if an entry with the same access token already exists
                await self.async_set_unique_id(user_input[CONF_ACCESS_TOKEN])
                self._abort_if_unique_id_configured()

                # Proceed to the budgets step
                return await self.async_step_budgets()

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

    async def async_step_budgets(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the step to select budgets."""
        errors = {}

        if user_input is not None:
            # Store the selected budgets and create the config entry
            selected_budget_ids = user_input["budgets"]
            LOGGER.info(self.budgets[0]["accounts"][0])
            selected_budgets = [
                {
                    "id": budget["id"],
                    "currency": budget["currency"],
                    "accounts": budget["accounts"],
                }
                for budget in self.budgets
                if budget["id"] in selected_budget_ids
            ]

            return self.async_create_entry(
                title=f"YNAB ({self.user_id})",
                data={
                    CONF_ACCESS_TOKEN: self.access_token,
                    "user_id": self.user_id,
                    "budgets": selected_budgets,
                },
            )

        # Fetch budgets if not already fetched
        if not self.budgets:
            try:
                self.budgets = await fetch_budgets(self.hass, self.access_token)
            except ConfigEntryAuthFailed:
                errors["base"] = "cannot_fetch_budgets"
            except Exception:  # noqa: BLE001
                LOGGER.exception("Unexpected exception during budget fetching")
                errors["base"] = "unknown"

        # Prepare the schema for budget selection
        budget_options = {budget["id"]: budget["name"] for budget in self.budgets}
        data_schema = vol.Schema(
            {
                vol.Required("budgets"): cv.multi_select(budget_options),
            }
        )

        return self.async_show_form(
            step_id="budgets",
            data_schema=data_schema,
            errors=errors,
        )
