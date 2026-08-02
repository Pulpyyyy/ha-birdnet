"""Exclusion of the large attributes from the history."""

from __future__ import annotations

from homeassistant.core import HomeAssistant, callback


@callback
def exclude_attributes(hass: HomeAssistant) -> set[str]:
    """These lists are of no use in the database and would inflate it."""
    return {"detections", "species", "bird_events"}
