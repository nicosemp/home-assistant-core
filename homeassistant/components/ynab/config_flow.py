"""Config flow for YNAB integration."""

from __future__ import annotations

from typing import Any, TypedDict

import voluptuous as vol
from ynab import ApiClient, ApiException, BudgetsApi, Configuration, UserApi

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_ACCESS_TOKEN
from homeassistant.helpers import config_validation as cv

from .const import DOMAIN, LOGGER


class AccountDict(TypedDict):
    """The processed Account data."""

    id: str
    name: str
    balance: int


class BudgetDict(TypedDict):
    """The processed Budget data."""

    id: str
    name: str
    currency: str
    accounts: list[AccountDict]


def _validate_token(access_token: str) -> str:
    """Validate the access token and return the user ID (blocking)."""

    configuration = Configuration(access_token=access_token)
    with ApiClient(configuration) as api_client:
        user_api = UserApi(api_client)
        response = user_api.get_user()
        LOGGER.info(response.data)
        return response.data.user.id


def _fetch_budgets(access_token: str) -> list[BudgetDict]:
    """Fetch the list of budgets from the YNAB API (blocking)."""

    configuration = Configuration(access_token=access_token)

    with ApiClient(configuration) as api_client:
        budgets_api = BudgetsApi(api_client)
        response = budgets_api.get_budgets(include_accounts=True)

        if not response.data or not response.data.budgets:
            return []

        return [
            {
                "id": budget.id,
                "name": budget.name,
                "currency": budget.currency_format.iso_code
                if budget.currency_format
                else "USD",
                "accounts": [
                    {
                        "id": account.id,
                        "name": account.name,
                        "balance": account.balance,
                    }
                    for account in (budget.accounts or [])
                    if not account.deleted and not account.closed
                ],
            }
            for budget in response.data.budgets
        ]


class YnabConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle the config flow for YNAB."""

    VERSION = 1
    MINOR_VERSION = 1

    def __init__(self) -> None:
        """Initialize the config flow."""
        self.access_token: str | None = None
        self.user_id: str | None = None
        self.budgets: list[BudgetDict] = []

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                user_id = await self.hass.async_add_executor_job(
                    _validate_token, user_input[CONF_ACCESS_TOKEN]
                )
            except ApiException:
                errors["base"] = "invalid_auth"
            else:
                self.access_token = user_input[CONF_ACCESS_TOKEN]
                self.user_id = user_id

                await self.async_set_unique_id(user_id)
                self._abort_if_unique_id_configured()

                return await self.async_step_budgets()

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_ACCESS_TOKEN): str,
                }
            ),
            errors=errors,
        )

    async def async_step_budgets(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the step to select budgets."""
        errors: dict[str, str] = {}

        if user_input is not None:
            selected_budget_ids = user_input["budgets"]
            selected_budgets = [
                {
                    "id": budget["id"],
                    "name": budget["name"],
                    "currency": budget["currency"],
                    "accounts": budget["accounts"],
                }
                for budget in self.budgets
                if budget["id"] in selected_budget_ids
            ]

            return self.async_create_entry(
                title=f"YNAB ({self.user_id})",  # FIXME: This should be `YNAB - [FIRST_NAME]` ideally, instead of using the id: https://github.com/ynab/ynab-sdk-python/issues/18
                data={
                    CONF_ACCESS_TOKEN: self.access_token,
                    "user_id": self.user_id,
                    "budgets": selected_budgets,
                },
            )

        if not self.budgets:
            if self.access_token is None:
                return await self.async_step_user()

            try:
                self.budgets = await self.hass.async_add_executor_job(
                    _fetch_budgets, self.access_token
                )
            except ApiException:
                errors["base"] = "cannot_fetch_budgets"

        budget_options = {budget["id"]: budget["name"] for budget in self.budgets}

        return self.async_show_form(
            step_id="budgets",
            data_schema=vol.Schema(
                {
                    vol.Required("budgets"): cv.multi_select(budget_options),
                }
            ),
            errors=errors,
        )
