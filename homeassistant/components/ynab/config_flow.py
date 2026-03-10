"""Config flow for YNAB integration."""

from __future__ import annotations

from typing import Any, TypedDict

import voluptuous as vol
from ynab import ApiClient, ApiException, BudgetsApi, Configuration, UserApi

from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlowWithReload,
)
from homeassistant.const import CONF_ACCESS_TOKEN
from homeassistant.core import callback
from homeassistant.helpers import config_validation as cv

from .const import DOMAIN, LOGGER


class AccountDict(TypedDict):
    """The processed Account data."""

    id: str
    name: str
    balance: int


class PlanDict(TypedDict):
    """The processed Plan data."""

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


def _fetch_plans(access_token: str) -> list[PlanDict]:
    """Fetch the list of plans from the YNAB API (blocking)."""

    configuration = Configuration(access_token=access_token)

    with ApiClient(configuration) as api_client:
        plans_api = BudgetsApi(api_client)
        response = plans_api.get_budgets(include_accounts=True)

        if not response.data or not response.data.budgets:
            return []

        return [
            {
                "id": plan.id,
                "name": plan.name,
                "currency": plan.currency_format.iso_code
                if plan.currency_format
                else "USD",
                "accounts": [
                    {
                        "id": account.id,
                        "name": account.name,
                        "balance": account.balance,
                    }
                    for account in (plan.accounts or [])
                    if not account.deleted and not account.closed
                ],
            }
            for plan in response.data.budgets
        ]


class YnabConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle the config flow for YNAB."""

    VERSION = 1
    MINOR_VERSION = 1

    def __init__(self) -> None:
        """Initialize the config flow."""
        self.access_token: str | None = None
        self.user_id: str | None = None
        self.plans: list[PlanDict] = []

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

                return await self.async_step_plans()

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_ACCESS_TOKEN): str,
                }
            ),
            errors=errors,
        )

    async def async_step_plans(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the step to select plans."""
        errors: dict[str, str] = {}

        if user_input is not None:
            selected_plan_ids = user_input["plans"]
            selected_plans = [
                {
                    "id": plan["id"],
                    "name": plan["name"],
                    "currency": plan["currency"],
                    "accounts": plan["accounts"],
                }
                for plan in self.plans
                if plan["id"] in selected_plan_ids
            ]

            return self.async_create_entry(
                title=f"YNAB ({self.user_id})",  # FIXME: This should be `YNAB - [FIRST_NAME]` ideally, instead of using the id: https://github.com/ynab/ynab-sdk-python/issues/18
                data={
                    CONF_ACCESS_TOKEN: self.access_token,
                    "user_id": self.user_id,
                },
                options={
                    "plans": selected_plans,
                },
            )

        if not self.plans:
            if self.access_token is None:
                return await self.async_step_user()

            try:
                self.plans = await self.hass.async_add_executor_job(
                    _fetch_plans, self.access_token
                )
            except ApiException:
                errors["base"] = "cannot_fetch_plans"

        plan_options = {plan["id"]: plan["name"] for plan in self.plans}

        return self.async_show_form(
            step_id="plans",
            data_schema=vol.Schema(
                {
                    vol.Required("plans"): cv.multi_select(plan_options),
                }
            ),
            errors=errors,
        )

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle reconfiguration of the access token."""
        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                user_id = await self.hass.async_add_executor_job(
                    _validate_token, user_input[CONF_ACCESS_TOKEN]
                )
            except ApiException:
                errors["base"] = "invalid_auth"
            else:
                await self.async_set_unique_id(user_id)
                self._abort_if_unique_id_mismatch()

                return self.async_update_reload_and_abort(
                    self._get_reconfigure_entry(),
                    data_updates={CONF_ACCESS_TOKEN: user_input[CONF_ACCESS_TOKEN]},
                )

        return self.async_show_form(
            step_id="reconfigure",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_ACCESS_TOKEN): str,
                }
            ),
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: ConfigEntry,
    ) -> YnabOptionsFlowHandler:
        """Get the options flow for this handler."""
        return YnabOptionsFlowHandler()


class YnabOptionsFlowHandler(OptionsFlowWithReload):
    """Handle the options flow for YNAB."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the options flow to select plans."""
        errors: dict[str, str] = {}

        if user_input is not None:
            selected_plan_ids = user_input["plans"]
            selected_plans = [
                plan for plan in self._plans if plan["id"] in selected_plan_ids
            ]

            return self.async_create_entry(
                title="",
                data={"plans": selected_plans},
            )

        access_token = self.config_entry.data[CONF_ACCESS_TOKEN]
        configured_plans: list[PlanDict] = self.config_entry.options.get("plans", [])
        configured_plan_ids = [plan["id"] for plan in configured_plans]

        try:
            self._plans: list[PlanDict] = await self.hass.async_add_executor_job(
                _fetch_plans, access_token
            )
        except ApiException:
            errors["base"] = "cannot_fetch_plans"
            self._plans = configured_plans

        plan_options = {plan["id"]: plan["name"] for plan in self._plans}

        # Ensure previously-selected plans still appear even if removed from YNAB
        for plan in configured_plans:
            if plan["id"] not in plan_options:
                plan_options[plan["id"]] = plan["name"]
                self._plans.append(plan)

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        "plans",
                        default=configured_plan_ids,
                    ): cv.multi_select(plan_options),
                }
            ),
            errors=errors,
        )
