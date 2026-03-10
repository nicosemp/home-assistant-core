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
    plans = entry.data["plans"]

    async_add_entities(
        YnabAccountSensor(
            coordinator,
            plan["id"],
            plan["currency"],
            plan["name"],
            account["id"],
            account["name"],
        )
        for plan in plans
        for account in plan["accounts"]
    )


class YnabAccountSensor(CoordinatorEntity[YnabDataUpdateCoordinator], SensorEntity):
    """Representation of a YNAB account sensor."""

    _attr_has_entity_name = True
    _attr_translation_key = "account_balance"

    def __init__(
        self,
        coordinator: YnabDataUpdateCoordinator,
        plan_id: str,
        plan_currency: str,
        plan_name: str,
        account_id: str,
        account_name: str,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)

        self._attr_unique_id = f"{plan_id}-{account_id}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, plan_id)},
            name=plan_name,
            manufacturer="YNAB",
            model="Plan",
            entry_type=DeviceEntryType.SERVICE,
        )
        self._attr_native_unit_of_measurement = plan_currency
        self._attr_name = account_name

        self._plan_id = plan_id
        self._account_id = account_id

    @property
    def native_value(self) -> float | None:
        """Return the state of the sensor."""

        if not self.coordinator.data:
            return None

        for plan in self.coordinator.data:
            if plan.id == self._plan_id:
                for account in plan.accounts or []:
                    if account.id == self._account_id:
                        return account.balance / 1000
        return None
