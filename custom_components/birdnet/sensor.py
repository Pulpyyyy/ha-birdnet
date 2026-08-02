"""Capteurs BirdNET."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.const import PERCENTAGE, EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import BirdNetConfigEntry, BirdNetCoordinator
from .entity import BirdNetEntity

# Nombre de détections détaillées exposées en attribut (les compteurs et le
# résumé par espèce, eux, portent sur la totalité de la journée).
ATTR_LOG_LIMIT = 50


async def async_setup_entry(
    hass: HomeAssistant,
    entry: BirdNetConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Ajoute les capteurs."""
    coordinator = entry.runtime_data
    async_add_entities(
        [
            BirdNetLastDetectionSensor(coordinator),
            BirdNetConfidenceSensor(coordinator),
            BirdNetLastDetectionTimeSensor(coordinator),
            BirdNetDetectionCountSensor(coordinator),
            BirdNetSpeciesCountSensor(coordinator),
            BirdNetTopicSensor(coordinator),
        ]
    )


class BirdNetLastDetectionSensor(BirdNetEntity, SensorEntity):
    """Dernière espèce entendue, avec tout le contexte en attributs."""

    _attr_icon = "mdi:bird"

    def __init__(self, coordinator: BirdNetCoordinator) -> None:
        """Initialise le capteur principal."""
        super().__init__(coordinator, "last_detection")

    @property
    def native_value(self) -> str | None:
        """Nom commun de la dernière détection."""
        if (detection := self.coordinator.last_detection) is None:
            return None
        return detection.common_name[:255]

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Tout ce dont la carte a besoin, en une seule entité."""
        coordinator = self.coordinator
        detections = coordinator.detections_as_dicts()
        species = coordinator.species_summary()

        attributes: dict[str, Any] = {
            "detection_count": len(coordinator.detections),
            "species_count": len(species),
            "species": species,
            "detections": detections[:ATTR_LOG_LIMIT],
            # Compatibilité avec les template sensors du tuto HACF.
            "bird_events": [
                {
                    "name": item["name"],
                    "confidence": item["confidence"],
                    "time": item["time"][:5],
                }
                for item in detections[:ATTR_LOG_LIMIT]
            ],
        }

        if (detection := coordinator.last_detection) is not None:
            attributes |= {
                "common_name": detection.common_name,
                "scientific_name": detection.scientific_name,
                "confidence": detection.confidence_pct,
                "confidence_score": detection.confidence,
                "time": detection.detected_at.strftime("%H:%M:%S"),
                "date": detection.detected_at.strftime("%Y-%m-%d"),
                "timestamp": detection.detected_at.isoformat(),
                "image": detection.image_url,
                "link": detection.link,
                "audio": detection.audio_url,
                "latitude": detection.latitude,
                "longitude": detection.longitude,
                "species_code": detection.species_code,
            }
        return attributes


class BirdNetConfidenceSensor(BirdNetEntity, SensorEntity):
    """Confiance de la dernière détection."""

    _attr_icon = "mdi:shield-check"
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_suggested_display_precision = 0

    def __init__(self, coordinator: BirdNetCoordinator) -> None:
        """Initialise le capteur de confiance."""
        super().__init__(coordinator, "confidence")

    @property
    def native_value(self) -> float | None:
        """Confiance en pourcentage."""
        if (detection := self.coordinator.last_detection) is None:
            return None
        return detection.confidence_pct


class BirdNetLastDetectionTimeSensor(BirdNetEntity, SensorEntity):
    """Horodatage de la dernière détection."""

    _attr_icon = "mdi:clock-outline"
    _attr_device_class = SensorDeviceClass.TIMESTAMP

    def __init__(self, coordinator: BirdNetCoordinator) -> None:
        """Initialise le capteur d'horodatage."""
        super().__init__(coordinator, "last_detection_time")

    @property
    def native_value(self) -> datetime | None:
        """Date et heure de la dernière détection."""
        if (detection := self.coordinator.last_detection) is None:
            return None
        return detection.detected_at


class BirdNetDetectionCountSensor(BirdNetEntity, SensorEntity):
    """Nombre de détections depuis minuit."""

    # Pas d'unité : elle ne serait pas traduite et resterait en français.
    _attr_icon = "mdi:counter"
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator: BirdNetCoordinator) -> None:
        """Initialise le compteur de détections."""
        super().__init__(coordinator, "detections_today")

    @property
    def native_value(self) -> int:
        """Total du jour."""
        return len(self.coordinator.detections)


class BirdNetSpeciesCountSensor(BirdNetEntity, SensorEntity):
    """Nombre d'espèces différentes depuis minuit."""

    _attr_icon = "mdi:format-list-bulleted"
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator: BirdNetCoordinator) -> None:
        """Initialise le compteur d'espèces."""
        super().__init__(coordinator, "species_today")

    @property
    def native_value(self) -> int:
        """Nombre d'espèces distinctes."""
        return len({item.common_name.lower() for item in self.coordinator.detections})

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Détail par espèce."""
        return {"species": self.coordinator.species_summary()}


class BirdNetTopicSensor(BirdNetEntity, SensorEntity):
    """Diagnostic : topic écouté et messages reçus."""

    _attr_icon = "mdi:transit-connection-variant"
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_entity_registry_enabled_default = False

    def __init__(self, coordinator: BirdNetCoordinator) -> None:
        """Initialise le capteur de diagnostic."""
        super().__init__(coordinator, "mqtt_topic")

    @property
    def native_value(self) -> str:
        """Topic MQTT."""
        return self.coordinator.topic

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Compteurs utiles au dépannage."""
        return {
            "messages_received": self.coordinator.messages_received,
            "min_confidence": self.coordinator.min_confidence,
            "excluded_species": self.coordinator.excluded_species,
            "last_error": self.coordinator.last_error,
        }
