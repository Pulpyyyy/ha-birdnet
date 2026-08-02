"""Entité événement : point d'entrée idéal pour les automatisations."""

from __future__ import annotations

from homeassistant.components.event import EventEntity
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import BirdNetConfigEntry, BirdNetCoordinator
from .entity import BirdNetEntity

EVENT_DETECTION = "detection"


async def async_setup_entry(
    hass: HomeAssistant,
    entry: BirdNetConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Ajoute l'entité événement."""
    async_add_entities([BirdNetDetectionEvent(entry.runtime_data)])


class BirdNetDetectionEvent(BirdNetEntity, EventEntity):
    """Se déclenche à chaque nouvelle détection retenue."""

    _attr_icon = "mdi:bird"
    _attr_event_types = [EVENT_DETECTION]

    def __init__(self, coordinator: BirdNetCoordinator) -> None:
        """Initialise l'entité événement."""
        super().__init__(coordinator, "detection")
        self._last_key: str | None = self._detection_key()

    @callback
    def _detection_key(self) -> str | None:
        """Identifiant de la dernière détection, pour éviter les doublons."""
        if (detection := self.coordinator.last_detection) is None:
            return None
        return f"{detection.detected_at.isoformat()}|{detection.common_name}"

    @callback
    def _handle_coordinator_update(self) -> None:
        """Déclenche l'événement uniquement sur une détection inédite."""
        key = self._detection_key()
        if key is None or key == self._last_key:
            return
        self._last_key = key
        detection = self.coordinator.last_detection
        assert detection is not None
        self._trigger_event(
            EVENT_DETECTION, self.coordinator.detection_as_dict(detection)
        )
        self.async_write_ha_state()
