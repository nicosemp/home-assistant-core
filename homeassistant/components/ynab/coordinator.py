"""Coordinator for YNAB integration."""

import asyncio
from datetime import timedelta
import functools

from ynab import ApiClient, ApiException, BudgetsApi, Configuration

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DOMAIN, LOGGER

SCAN_INTERVAL = timedelta(seconds=30)


class YnabDataUpdateCoordinator(DataUpdateCoordinator):
    """Class to manage fetching YNAB data from the API."""

    def __init__(self, hass: HomeAssistant, access_token: str) -> None:
        """Initialize the coordinator."""
        self._access_token = access_token
        self._configuration = Configuration(access_token=self._access_token)
        self._budgets = None
        super().__init__(
            hass,
            LOGGER,
            name=DOMAIN,
            update_interval=SCAN_INTERVAL,
        )

    async def _async_update_data(self) -> str:
        """Fetch data from the YNAB API."""
        try:
            with ApiClient(self._configuration) as api_client:
                budgets_api = BudgetsApi(api_client)
                loop = asyncio.get_event_loop()
                response = await loop.run_in_executor(
                    None,
                    functools.partial(budgets_api.get_budgets, include_accounts=True),
                )
                self._budgets = response.data.budgets
                return self._budgets
        except ApiException as err:
            raise UpdateFailed(f"Error fetching data from YNAB API: {err}") from err


# async def fetch_budgets(hass: HomeAssistant, access_token: str) -> list[dict[str, str]]:
#     """Fetch the list of budgets from the YNAB API."""
#     configuration = Configuration(access_token=access_token)

#     try:
#         with ApiClient(configuration) as api_client:
#             budgets_api = BudgetsApi(api_client)
#             loop = asyncio.get_event_loop()
#             response = await loop.run_in_executor(
#                 None, functools.partial(budgets_api.get_budgets, include_accounts=True)
#             )
#             budgets = response.data.budgets
#             return [
#                 {
#                     "id": budget.id,
#                     "name": budget.name,
#                     "currency": budget.currency_format.iso_code,
#                     "accounts": [
#                         {
#                             "id": account.id,
#                             "name": account.name,
#                             "balance": account.balance,
#                         }
#                         for account in budget.accounts
#                         if account.deleted is False and account.closed is False
#                     ],
#                 }
#                 for budget in budgets
#             ]
#     except ApiException as err:
#         LOGGER.error("Error fetching budgets from YNAB API: %s", err)
#         raise ConfigEntryAuthFailed("Failed to fetch budgets") from err
