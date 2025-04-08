"""Platform for retrieving YNAB data."""

import logging

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_ACCESS_TOKEN
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import YnabDataUpdateCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up YNAB sensors from a config entry."""
    access_token = entry.data[CONF_ACCESS_TOKEN]
    budgets = entry.data["budgets"]

    coordinator = YnabDataUpdateCoordinator(hass, access_token)
    await coordinator.async_config_entry_first_refresh()

    account_entities = []

    for budget in budgets:
        budget_id = budget["id"]
        budget_currency = budget["currency"]
        for account in budget["accounts"]:
            account_id = account["id"]
            account_name = account["name"]
            account_balance = account["balance"]
            account_entities.append(
                YnabAccountSensor(
                    coordinator,
                    budget_id,
                    budget_currency,
                    account_id,
                    account_name,
                    account_balance,
                )
            )

    async_add_entities(account_entities, True)


class YnabAccountSensor(CoordinatorEntity, SensorEntity):
    """Representation of a YNAB account sensor."""

    def __init__(
        self,
        coordinator: YnabDataUpdateCoordinator,
        budget_id: str,
        budget_currency: str,
        account_id: str,
        account_name: str,
        account_balance: int,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)  # Link the sensor to the coordinator

        self._attr_name = f"{account_name} Balance"
        self._attr_unique_id = f"{budget_id}-{account_id}"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, budget_id)},
            "name": f"Budget {budget_id}",
            "manufacturer": "YNAB",
            "model": "Budget",
        }
        self._attr_native_unit_of_measurement = budget_currency
        self._attr_icon = "mdi:currency-eur"

        self._state = account_balance / 1000  # Convert milliunits to units
        self._budget_id = budget_id
        self._account_id = account_id

    @property
    def state(self) -> float:
        """Return the state of the sensor."""
        # Find the latest account balance from the coordinator's data
        for budget in self.coordinator.data:
            if budget.id == self._budget_id:
                for account in budget.accounts:
                    if account.id == self._account_id:
                        return account.balance / 1000  # Convert milliunits to units
        return None  # Return None if the account is not found
