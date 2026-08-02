"""Picture of the latest detected species."""

from __future__ import annotations

from homeassistant.components.image import ImageEntity
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.util import dt as dt_util

from .coordinator import BirdNetConfigEntry, BirdNetCoordinator
from .entity import BirdNetEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: BirdNetConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Add the image entity."""
    async_add_entities([BirdNetImage(hass, entry.runtime_data)])


class BirdNetImage(BirdNetEntity, ImageEntity):
    """Species picture, from Flickr, Wikimedia or BirdNET-Go depending on the source."""

    def __init__(self, hass: HomeAssistant, coordinator: BirdNetCoordinator) -> None:
        """Initialise the image entity."""
        BirdNetEntity.__init__(self, coordinator, "last_detection")
        ImageEntity.__init__(self, hass, verify_ssl=True)
        self._attr_image_url = None
        self._refresh_url()

    @callback
    def _refresh_url(self) -> bool:
        """Update the URL; return True when it changed."""
        detection = self.coordinator.last_detection
        url = detection.image_url if detection else None
        if url == self._attr_image_url:
            return False
        self._attr_image_url = url
        self._attr_image_last_updated = dt_util.utcnow()
        self._cached_image = None
        return True

    @callback
    def _handle_coordinator_update(self) -> None:
        """Reload the picture when the species changes."""
        self._refresh_url()
        self.async_write_ha_state()
