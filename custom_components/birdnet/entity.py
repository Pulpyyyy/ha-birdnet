"""Entité de base BirdNET."""

from __future__ import annotations

from homeassistant.core import callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity import Entity

from .const import DEFAULT_NAME, DOMAIN
from .coordinator import BirdNetCoordinator


class BirdNetEntity(Entity):
    """Base commune : rattachement à l'appareil et abonnement au collecteur."""

    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(self, coordinator: BirdNetCoordinator, key: str) -> None:
        """Initialise l'entité."""
        self.coordinator = coordinator
        self._attr_unique_id = f"{coordinator.entry.entry_id}_{key}"
        self._attr_translation_key = key
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, coordinator.entry.entry_id)},
            name=DEFAULT_NAME,
            manufacturer="BirdNET",
            model="BirdNET-Pi / BirdNET-Go (MQTT)",
        )

    async def async_added_to_hass(self) -> None:
        """S'abonne aux mises à jour du collecteur."""
        await super().async_added_to_hass()
        self.async_on_remove(
            self.coordinator.async_add_listener(self._handle_coordinator_update)
        )

    @callback
    def _handle_coordinator_update(self) -> None:
        """Réagit à une nouvelle détection."""
        self.async_write_ha_state()
