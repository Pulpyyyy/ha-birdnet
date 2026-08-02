"""The BirdNET integration (BirdNET-Pi / BirdNET-Go) over MQTT."""

from __future__ import annotations

import logging
import secrets

from homeassistant.components import mqtt, websocket_api
from homeassistant.const import EVENT_HOMEASSISTANT_STARTED, Platform
from homeassistant.core import CoreState, HomeAssistant, ServiceCall, callback
from homeassistant.exceptions import ConfigEntryNotReady, ServiceValidationError
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.typing import ConfigType
import voluptuous as vol

from .const import CONF_CLIP_SECRET, DOMAIN, INTEGRATION_VERSION
from .coordinator import BirdNetConfigEntry, BirdNetCoordinator
from .frontend import JSModuleRegistration
from .http import async_register_clip_view
from .models import Detection

_LOGGER = logging.getLogger(__name__)

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)

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


@websocket_api.websocket_command({vol.Required("type"): f"{DOMAIN}/version"})
@callback
def websocket_get_version(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict,
) -> None:
    """Return the integration version to the card.

    A versioned URL is not enough: a cached page (especially in the companion
    app) keeps loading the old module. The card compares both versions and
    offers a reload when they differ.
    """
    connection.send_result(msg["id"], {"version": INTEGRATION_VERSION})


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Register the card once, whatever the number of config entries."""
    websocket_api.async_register_command(hass, websocket_get_version)

    async def _setup_frontend(_event=None) -> None:
        await JSModuleRegistration(hass).async_register()

    # Before EVENT_HOMEASSISTANT_STARTED, hass.data["lovelace"] does not exist
    # yet: registering the resource would be silently ignored.
    if hass.state is CoreState.running:
        await _setup_frontend()
    else:
        hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STARTED, _setup_frontend)

    return True


async def async_setup_entry(hass: HomeAssistant, entry: BirdNetConfigEntry) -> bool:
    """Set up a BirdNET instance."""
    if not await mqtt.async_wait_for_mqtt_client(hass):
        raise ConfigEntryNotReady("The MQTT client is not available")

    # Entries created before the audio relay existed: fill in the secret. No
    # listener is attached yet at this point, so the update does not trigger a
    # reload.
    if CONF_CLIP_SECRET not in entry.data:
        hass.config_entries.async_update_entry(
            entry,
            data={**entry.data, CONF_CLIP_SECRET: secrets.token_hex(32)},
        )
    async_register_clip_view(hass)

    coordinator = BirdNetCoordinator(hass, entry)
    await coordinator.async_setup()
    entry.runtime_data = coordinator

    _async_register_services(hass)

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_async_reload_entry))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: BirdNetConfigEntry) -> bool:
    """Unload a BirdNET instance."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        await entry.runtime_data.async_shutdown()
    return unload_ok


async def async_remove_entry(hass: HomeAssistant, entry: BirdNetConfigEntry) -> None:
    """Remove the Lovelace resource when the last entry goes away."""
    if hass.config_entries.async_entries(DOMAIN):
        return
    await JSModuleRegistration(hass).async_unregister()


async def _async_reload_entry(hass: HomeAssistant, entry: BirdNetConfigEntry) -> None:
    """Reload the entry after the options changed."""
    await hass.config_entries.async_reload(entry.entry_id)


@callback
def _async_register_services(hass: HomeAssistant) -> None:
    """Register the services once."""
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
                raise ServiceValidationError(f"Unknown BirdNET entry: {entry_id}")
        return [entry.runtime_data for entry in entries]

    async def _handle_clear_log(call: ServiceCall) -> None:
        for coordinator in _coordinators(call):
            coordinator.async_clear_log()

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
            raise ServiceValidationError("Unable to build the detection")
        for coordinator in _coordinators(call):
            coordinator.async_add_detection(detection)

    hass.services.async_register(
        DOMAIN, SERVICE_CLEAR_LOG, _handle_clear_log, schema=_ENTRY_ID_SCHEMA
    )
    hass.services.async_register(
        DOMAIN, SERVICE_SIMULATE_DETECTION, _handle_simulate, schema=_SIMULATE_SCHEMA
    )
