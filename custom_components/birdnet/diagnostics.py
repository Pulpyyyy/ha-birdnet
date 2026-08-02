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
    last = coordinator.last_detection.as_dict() if coordinator.last_detection else None
    if last:
        last = {k: v for k, v in last.items() if k not in TO_REDACT}

    return {
        "options": {
            "topic": coordinator.topic,
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
