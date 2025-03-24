"""Coordinator for YNAB integration."""

import asyncio
from datetime import timedelta

from ynab import ApiClient, ApiException, Configuration, UserApi

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DOMAIN, LOGGER

SCAN_INTERVAL = timedelta(minutes=60)


class YnabDataUpdateCoordinator(DataUpdateCoordinator):
    """Class to manage fetching YNAB data from the API."""

    def __init__(self, hass: HomeAssistant, access_token: str) -> None:
        """Initialize the coordinator."""
        self._access_token = access_token
        self._user_id = None
        super().__init__(
            hass,
            LOGGER,
            name=DOMAIN,
            update_interval=SCAN_INTERVAL,
        )

    async def _async_update_data(self) -> str:
        """Fetch data from the YNAB API."""
        configuration = Configuration(access_token=self._access_token)
        try:
            with ApiClient(configuration) as api_client:
                user_api = UserApi(api_client)
                loop = asyncio.get_event_loop()
                response = await loop.run_in_executor(None, user_api.get_user)
                self._user_id = response.data.user.id
                return self._user_id
        except ApiException as err:
            raise UpdateFailed(f"Error fetching data from YNAB API: {err}") from err

    @property
    def user_id(self) -> str:
        """Return the user ID."""
        return self._user_id
