"""Base BirdNET entity."""

from __future__ import annotations

from homeassistant.core import callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity import Entity

from .const import DEFAULT_NAME, DOMAIN
from .coordinator import BirdNetCoordinator


class BirdNetEntity(Entity):
    """Shared base: device binding and subscription to the coordinator."""

    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(self, coordinator: BirdNetCoordinator, key: str) -> None:
        """Initialise the entity."""
        self.coordinator = coordinator
        self._key = key
        self._attr_unique_id = f"{coordinator.entry.entry_id}_{key}"
        self._attr_translation_key = key
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, coordinator.entry.entry_id)},
            name=DEFAULT_NAME,
            manufacturer="BirdNET",
            model="BirdNET-Pi / BirdNET-Go (MQTT)",
        )

    @property
    def suggested_object_id(self) -> str | None:
        """Keep the entity ids in English, whatever the user's language.

        Home Assistant derives the entity id from the translated name, so a
        French install would create sensor.birdnet_derniere_detection. Deriving
        it from the translation key instead keeps the ids stable and documented,
        while the displayed names stay translated.
        """
        return self._key

    async def async_added_to_hass(self) -> None:
        """Subscribe to coordinator updates."""
        await super().async_added_to_hass()
        self.async_on_remove(
            self.coordinator.async_add_listener(self._handle_coordinator_update)
        )

    @callback
    def _handle_coordinator_update(self) -> None:
        """React to a new detection."""
        self.async_write_ha_state()
