"""Diagnostics for the BirdNET integration."""

from __future__ import annotations

from typing import Any

from homeassistant.core import HomeAssistant

from .coordinator import BirdNetConfigEntry

TO_REDACT = {"latitude", "longitude"}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: BirdNetConfigEntry
) -> dict[str, Any]:
    """Return the information useful for troubleshooting."""
    coordinator = entry.runtime_data
    last = None
    if (detection := coordinator.last_detection) is not None:
        # The coordinates come from the entity, not from as_dict(), so they have
        # to be removed here for the redaction to be more than an intention.
        last = detection.as_dict() | {
            "latitude": detection.latitude,
            "longitude": detection.longitude,
        }
        last = {k: v for k, v in last.items() if k not in TO_REDACT}

    return {
        "options": {
            "topic": coordinator.topic,
            "base_url": coordinator.base_url,
            "min_confidence": coordinator.min_confidence,
            "excluded_species": coordinator.excluded_species,
            "max_detections": coordinator.max_detections,
        },
        "messages_received": coordinator.messages_received,
        "duplicates_ignored": coordinator.duplicates_ignored,
        "last_error": coordinator.last_error,
        "last_detection": last,
        "detections_today": len(coordinator.detections),
        "species_today": coordinator.species_summary(),
    }
