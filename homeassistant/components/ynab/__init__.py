"""The YNAB integration."""

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_ACCESS_TOKEN
from homeassistant.core import HomeAssistant

from .coordinator import YnabDataUpdateCoordinator

type YnabConfigEntry = ConfigEntry[YnabDataUpdateCoordinator]

PLATFORMS = ["sensor"]


async def async_setup_entry(hass: HomeAssistant, entry: YnabConfigEntry) -> bool:
    """Set up YNAB from a config entry."""
    coordinator = YnabDataUpdateCoordinator(hass, entry, entry.data[CONF_ACCESS_TOKEN])
    await coordinator.async_config_entry_first_refresh()

    entry.runtime_data = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: YnabConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
