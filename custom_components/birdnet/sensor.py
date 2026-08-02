"""BirdNET sensors."""

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

# Number of detailed detections exposed as an attribute. The counters and the
# per-species summary still cover the whole day.
ATTR_LOG_LIMIT = 50


async def async_setup_entry(
    hass: HomeAssistant,
    entry: BirdNetConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Add the sensors."""
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
    """Latest species heard, with all the context as attributes."""

    _attr_icon = "mdi:bird"

    def __init__(self, coordinator: BirdNetCoordinator) -> None:
        """Initialise the main sensor."""
        super().__init__(coordinator, "last_detection")

    @property
    def native_value(self) -> str | None:
        """Common name of the latest detection."""
        if (detection := self.coordinator.last_detection) is None:
            return None
        return detection.common_name[:255]

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Everything the card needs, on a single entity."""
        coordinator = self.coordinator
        detections = coordinator.detections_as_dicts()
        species = coordinator.species_summary()

        attributes: dict[str, Any] = {
            "detection_count": len(coordinator.detections),
            "species_count": len(species),
            "species": species,
            "detections": detections[:ATTR_LOG_LIMIT],
            # Kept for compatibility with the community template sensors.
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
            latest = coordinator.detection_as_dict(detection) | {
                "latitude": detection.latitude,
                "longitude": detection.longitude,
            }
            # "name" only makes sense inside the lists, not at the top level.
            latest.pop("name", None)
            # A field missing from the payload (BirdNET-Pi sends neither a
            # species code nor coordinates) clutters the entity for nothing:
            # only publish what actually exists.
            attributes |= {
                key: value for key, value in latest.items() if value is not None
            }
        return attributes


class BirdNetConfidenceSensor(BirdNetEntity, SensorEntity):
    """Confidence of the latest detection.

    Disabled by default: it only republishes the `confidence` attribute of the
    main sensor. Enable it to keep a history or to show it on its own row.
    """

    _attr_icon = "mdi:shield-check"
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_suggested_display_precision = 0
    _attr_entity_registry_enabled_default = False

    def __init__(self, coordinator: BirdNetCoordinator) -> None:
        """Initialise the confidence sensor."""
        super().__init__(coordinator, "confidence")

    @property
    def native_value(self) -> float | None:
        """Confidence as a percentage."""
        if (detection := self.coordinator.last_detection) is None:
            return None
        return detection.confidence_pct


class BirdNetLastDetectionTimeSensor(BirdNetEntity, SensorEntity):
    """Timestamp of the latest detection.

    Disabled by default: it only republishes the `timestamp` attribute of the
    main sensor. Enable it for a relative "heard 5 minutes ago" display.
    """

    _attr_icon = "mdi:clock-outline"
    _attr_device_class = SensorDeviceClass.TIMESTAMP
    _attr_entity_registry_enabled_default = False

    def __init__(self, coordinator: BirdNetCoordinator) -> None:
        """Initialise the timestamp sensor."""
        super().__init__(coordinator, "last_detection_time")

    @property
    def native_value(self) -> datetime | None:
        """Date and time of the latest detection."""
        if (detection := self.coordinator.last_detection) is None:
            return None
        return detection.detected_at


class BirdNetDetectionCountSensor(BirdNetEntity, SensorEntity):
    """Number of detections since midnight."""

    # No unit: units are not translated, so it would show English wording in
    # every other language.
    _attr_icon = "mdi:counter"
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator: BirdNetCoordinator) -> None:
        """Initialise the detection counter."""
        super().__init__(coordinator, "detections_today")

    @property
    def native_value(self) -> int:
        """Total for the day."""
        return len(self.coordinator.detections)


class BirdNetSpeciesCountSensor(BirdNetEntity, SensorEntity):
    """Number of distinct species since midnight."""

    _attr_icon = "mdi:format-list-bulleted"
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator: BirdNetCoordinator) -> None:
        """Initialise the species counter."""
        super().__init__(coordinator, "species_today")

    @property
    def native_value(self) -> int:
        """Number of distinct species."""
        return len({item.common_name.lower() for item in self.coordinator.detections})

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Per-species breakdown."""
        return {"species": self.coordinator.species_summary()}


class BirdNetTopicSensor(BirdNetEntity, SensorEntity):
    """Diagnostic: topic being listened to and messages received."""

    _attr_icon = "mdi:transit-connection-variant"
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_entity_registry_enabled_default = False

    def __init__(self, coordinator: BirdNetCoordinator) -> None:
        """Initialise the diagnostic sensor."""
        super().__init__(coordinator, "mqtt_topic")

    @property
    def native_value(self) -> str:
        """MQTT topic."""
        return self.coordinator.topic

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Counters useful for troubleshooting."""
        return {
            "messages_received": self.coordinator.messages_received,
            "duplicates_ignored": self.coordinator.duplicates_ignored,
            "min_confidence": self.coordinator.min_confidence,
            "excluded_species": self.coordinator.excluded_species,
            "last_error": self.coordinator.last_error,
        }
