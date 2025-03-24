"""Platform for retrieving YNAB data."""

from datetime import timedelta
import logging

import voluptuous as vol

from homeassistant.components.sensor import (
    PLATFORM_SCHEMA as SENSOR_PLATFORM_SCHEMA,
    SensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_ACCESS_TOKEN
from homeassistant.core import HomeAssistant
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .coordinator import YnabDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)

# Time between updating data from the YNAB API
SCAN_INTERVAL = timedelta(minutes=60)

PLATFORM_SCHEMA = SENSOR_PLATFORM_SCHEMA.extend(
    {
        vol.Required(CONF_ACCESS_TOKEN): cv.string,
    }
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up YNAB sensors from a config entry."""
    # title = entry.data.get("title")  # The user ID is stored in the config entry title
    # user_id = entry.data.get("user_id")  # Retrieve the user_id from the config entry
    # async_add_entities([YnabUserIdSensor(user_id)], True)

    access_token = entry.data[CONF_ACCESS_TOKEN]
    coordinator = YnabDataUpdateCoordinator(hass, access_token)
    await coordinator.async_config_entry_first_refresh()

    async_add_entities([YnabUserIdSensor(coordinator)], True)


class YnabUserIdSensor(CoordinatorEntity, SensorEntity):
    """Representation of a YNAB User ID sensor."""

    def __init__(self, coordinator: YnabDataUpdateCoordinator) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._attr_name = "YNAB User ID"
        self._attr_unique_id = f"ynab_user_id_{coordinator.user_id}"
        self._attr_icon = "mdi:account"
        # self._state = user_id

    @property
    def state(self) -> str:
        """Return the state of the sensor."""
        return self.coordinator.data


# async def async_setup_platform(
#     hass: HomeAssistant,
#     config: ConfigType,
#     async_add_entities: AddEntitiesCallback,
#     discovery_info: DiscoveryInfoType | None = None,
# ) -> bool:
#     """Set up the YNAB from configuration.yaml."""
#     configuration = ynab.Configuration(access_token=config[CONF_ACCESS_TOKEN])
#     api_client = ynab.ApiClient(configuration)
#     user_api = ynab.UserApi(api_client)
#     sensor = YnabSensor(user_api)
#     async_add_entities([sensor], True)


# class YnabSensor(Entity):
#     """Representation of a YNAB sensor."""

#     def __init__(self, user_api: ynab.UserApi) -> None:
#         """Initialize the sensor."""
#         self._user_api = user_api
#         self._state = None
#         self._attr_name = "YNAB"
#         self._attr_icon = ICON

#     async def async_update(self):
#         """Get the latest data from the YNAB API."""
#         loop = asyncio.get_event_loop()
#         try:
#             get_user_response = await loop.run_in_executor(
#                 None, self._user_api.get_user
#             )
#             self._state = get_user_response.data.user.id
#         except ynab.ApiException as err:
#             _LOGGER.error("Error connecting to YNAB API: %s", err)
#             self._state = None

#     @property
#     def state(self) -> str:
#         """Return the state of the sensor."""
#         return self._state
