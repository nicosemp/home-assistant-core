"""Coordinator for YNAB integration."""

from datetime import timedelta

from ynab import ApiClient, ApiException, BudgetsApi, BudgetSummary, Configuration

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DOMAIN, LOGGER

SCAN_INTERVAL = timedelta(seconds=30)


class YnabDataUpdateCoordinator(DataUpdateCoordinator[list[BudgetSummary]]):
    """Class to manage fetching YNAB data from the API."""

    def __init__(
        self, hass: HomeAssistant, config_entry: ConfigEntry, access_token: str
    ) -> None:
        """Initialize the coordinator."""
        self._access_token = access_token
        self._configuration = Configuration(access_token=self._access_token)
        super().__init__(
            hass,
            LOGGER,
            name=DOMAIN,
            update_interval=SCAN_INTERVAL,
            config_entry=config_entry,
        )

    def _fetch_budgets(self) -> list:
        """Fetch budgets from the YNAB API (blocking)."""
        with ApiClient(self._configuration) as api_client:
            budgets_api = BudgetsApi(api_client)
            response = budgets_api.get_budgets(include_accounts=True)
            return response.data.budgets

    async def _async_update_data(self) -> list:
        """Fetch data from the YNAB API."""
        try:
            return await self.hass.async_add_executor_job(self._fetch_budgets)
        except ApiException as err:
            raise UpdateFailed(f"Error fetching data from YNAB API: {err}") from err
