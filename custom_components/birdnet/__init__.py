"""Intégration BirdNET (BirdNET-Pi / BirdNET-Go) via MQTT."""

from __future__ import annotations

import logging

from homeassistant.components import mqtt
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, ServiceCall, callback
from homeassistant.exceptions import ConfigEntryNotReady, ServiceValidationError
from homeassistant.helpers import config_validation as cv
import voluptuous as vol

from .const import DOMAIN
from .coordinator import BirdNetConfigEntry, BirdNetCoordinator
from .frontend import async_register_frontend
from .models import Detection

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.EVENT, Platform.IMAGE, Platform.SENSOR]

SERVICE_CLEAR_LOG = "clear_log"
SERVICE_SIMULATE_DETECTION = "simulate_detection"

_ENTRY_ID_SCHEMA = vol.Schema({vol.Optional("entry_id"): cv.string})
_SIMULATE_SCHEMA = _ENTRY_ID_SCHEMA.extend(
    {
        vol.Required("common_name"): cv.string,
        vol.Optional("scientific_name"): cv.string,
        vol.Optional("confidence"): vol.Coerce(float),
        vol.Optional("image"): cv.string,
        vol.Optional("link"): cv.string,
    }
)


async def async_setup_entry(hass: HomeAssistant, entry: BirdNetConfigEntry) -> bool:
    """Configure une instance BirdNET."""
    if not await mqtt.async_wait_for_mqtt_client(hass):
        raise ConfigEntryNotReady("Le client MQTT n'est pas disponible")

    coordinator = BirdNetCoordinator(hass, entry)
    await coordinator.async_setup()
    entry.runtime_data = coordinator

    await async_register_frontend(hass)
    _async_register_services(hass)

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_async_reload_entry))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: BirdNetConfigEntry) -> bool:
    """Décharge une instance BirdNET."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        await entry.runtime_data.async_shutdown()
    return unload_ok


async def _async_reload_entry(hass: HomeAssistant, entry: BirdNetConfigEntry) -> None:
    """Recharge l'entrée après modification des options."""
    await hass.config_entries.async_reload(entry.entry_id)


@callback
def _async_register_services(hass: HomeAssistant) -> None:
    """Enregistre les services une seule fois."""
    if hass.services.has_service(DOMAIN, SERVICE_CLEAR_LOG):
        return

    @callback
    def _coordinators(call: ServiceCall) -> list[BirdNetCoordinator]:
        entries: list[BirdNetConfigEntry] = hass.config_entries.async_loaded_entries(
            DOMAIN
        )
        if entry_id := call.data.get("entry_id"):
            entries = [entry for entry in entries if entry.entry_id == entry_id]
            if not entries:
                raise ServiceValidationError(f"Entrée BirdNET inconnue : {entry_id}")
        return [entry.runtime_data for entry in entries]

    async def _handle_clear_log(call: ServiceCall) -> None:
        for coordinator in _coordinators(call):
            coordinator.detections = []
            coordinator._notify()  # noqa: SLF001 - notification interne volontaire

    async def _handle_simulate(call: ServiceCall) -> None:
        payload = {
            "common_name": call.data["common_name"],
            "scientific_name": call.data.get("scientific_name"),
            "confidence_score": call.data.get("confidence", 0.95),
            "image": call.data.get("image"),
            "link": call.data.get("link"),
        }
        detection = Detection.from_payload(
            {k: v for k, v in payload.items() if v is not None}
        )
        if detection is None:
            raise ServiceValidationError("Impossible de construire la détection")
        for coordinator in _coordinators(call):
            coordinator.async_add_detection(detection)

    hass.services.async_register(
        DOMAIN, SERVICE_CLEAR_LOG, _handle_clear_log, schema=_ENTRY_ID_SCHEMA
    )
    hass.services.async_register(
        DOMAIN, SERVICE_SIMULATE_DETECTION, _handle_simulate, schema=_SIMULATE_SCHEMA
    )
