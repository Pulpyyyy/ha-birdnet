"""Publication de la carte Lovelace fournie avec l'intégration."""

from __future__ import annotations

import logging
from pathlib import Path

from homeassistant.components.http import StaticPathConfig
from homeassistant.core import HomeAssistant

from .const import CARD_FILENAME, DOMAIN, URL_BASE

_LOGGER = logging.getLogger(__name__)

_REGISTERED = f"{DOMAIN}_frontend_registered"


async def async_register_frontend(hass: HomeAssistant) -> None:
    """Sert la carte et l'ajoute aux ressources Lovelace si possible."""
    if hass.data.get(_REGISTERED):
        return
    hass.data[_REGISTERED] = True

    card_path = Path(__file__).parent / "frontend" / CARD_FILENAME
    card_url = f"{URL_BASE}/{CARD_FILENAME}"

    await hass.http.async_register_static_paths(
        [StaticPathConfig(card_url, str(card_path), cache_headers=False)]
    )

    version = hass.data.get(f"{DOMAIN}_version", "1.0.0")
    await _async_add_lovelace_resource(hass, f"{card_url}?v={version}")


async def _async_add_lovelace_resource(hass: HomeAssistant, url: str) -> None:
    """Ajoute (ou met à jour) la ressource dans un dashboard en mode storage."""
    lovelace = hass.data.get("lovelace")
    resources = getattr(lovelace, "resources", None)
    if resources is None:
        _LOGGER.info(
            "Lovelace en mode YAML : ajoutez manuellement la ressource module %s", url
        )
        return

    try:
        if not resources.loaded:
            await resources.async_load()
            resources.loaded = True

        base_url = url.split("?")[0]
        for item in resources.async_items():
            if str(item.get("url", "")).split("?")[0] != base_url:
                continue
            if item["url"] != url:
                await resources.async_update_item(item["id"], {"url": url})
            return

        await resources.async_create_item({"res_type": "module", "url": url})
        _LOGGER.info("Carte BirdNET ajoutée aux ressources Lovelace (%s)", url)
    except Exception:  # noqa: BLE001 - l'API Lovelace varie selon les versions
        _LOGGER.warning(
            "Ajout automatique de la ressource impossible. "
            "Ajoutez à la main : Paramètres > Tableaux de bord > Ressources > %s "
            "(type: module JavaScript)",
            url,
            exc_info=True,
        )
