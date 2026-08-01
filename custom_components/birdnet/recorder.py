"""Exclusion des gros attributs de l'historique."""

from __future__ import annotations

from homeassistant.core import HomeAssistant, callback


@callback
def exclude_attributes(hass: HomeAssistant) -> set[str]:
    """Ces listes n'ont aucun intérêt en base et la feraient gonfler."""
    return {"detections", "species", "bird_events"}
