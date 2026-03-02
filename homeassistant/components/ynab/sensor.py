"""Platform for retrieving YNAB data."""

from homeassistant.components.sensor import SensorEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import YnabConfigEntry
from .const import DOMAIN
from .coordinator import YnabDataUpdateCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: YnabConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up YNAB sensors from a config entry."""
    coordinator = entry.runtime_data
    budgets = entry.data["budgets"]

    async_add_entities(
        YnabAccountSensor(
            coordinator,
            budget["id"],
            budget["currency"],
            budget["name"],
            account["id"],
            account["name"],
        )
        for budget in budgets
        for account in budget["accounts"]
    )


class YnabAccountSensor(CoordinatorEntity[YnabDataUpdateCoordinator], SensorEntity):
    """Representation of a YNAB account sensor."""

    _attr_has_entity_name = True
    _attr_translation_key = "account_balance"

    def __init__(
        self,
        coordinator: YnabDataUpdateCoordinator,
        budget_id: str,
        budget_currency: str,
        budget_name: str,
        account_id: str,
        account_name: str,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)

        self._attr_unique_id = f"{budget_id}-{account_id}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, budget_id)},
            name=budget_name,
            manufacturer="YNAB",
            model="Budget",
            entry_type=DeviceEntryType.SERVICE,
        )
        self._attr_native_unit_of_measurement = budget_currency
        self._attr_name = account_name

        self._budget_id = budget_id
        self._account_id = account_id

    @property
    def native_value(self) -> float | None:
        """Return the state of the sensor."""

        if not self.coordinator.data:
            return None

        for budget in self.coordinator.data:
            if budget.id == self._budget_id:
                for account in budget.accounts or []:
                    if account.id == self._account_id:
                        return account.balance / 1000
        return None
