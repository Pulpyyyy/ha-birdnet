"""Enregistrement de la carte Lovelace livrée avec l'intégration.

Structure et séquence reprises du guide HACF « Carte Lovelace embarquée dans une
intégration Home Assistant » : chemin statique toujours enregistré, ressource
ajoutée uniquement en mode stockage, et attente du chargement des ressources
Lovelace avant d'y toucher.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from homeassistant.components.http import StaticPathConfig
from homeassistant.core import HomeAssistant
from homeassistant.helpers.event import async_call_later

from ..const import CARD_FILENAME, JSMODULES, URL_BASE

_LOGGER = logging.getLogger(__name__)

RETRY_DELAY = 5
MAX_ATTEMPTS = 12


class JSModuleRegistration:
    """Publie les modules JavaScript de l'intégration."""

    def __init__(self, hass: HomeAssistant) -> None:
        """Initialise le registraire."""
        self.hass = hass
        self.lovelace = hass.data.get("lovelace")

    @property
    def _mode(self) -> str:
        """Mode de Lovelace : storage ou yaml."""
        return getattr(
            self.lovelace, "mode", getattr(self.lovelace, "resource_mode", "yaml")
        )

    async def async_register(self) -> None:
        """Sert les fichiers puis référence les modules dans Lovelace."""
        await self._async_register_path()

        if self._mode != "storage":
            _LOGGER.info(
                "Lovelace en mode YAML : ajoutez la ressource à la main -> "
                "url: %s/%s , type: module",
                URL_BASE,
                CARD_FILENAME,
            )
            return

        await self._async_wait_for_lovelace_resources()

    async def _async_register_path(self) -> None:
        """Enregistre le chemin HTTP statique servant le dossier frontend."""
        try:
            await self.hass.http.async_register_static_paths(
                [StaticPathConfig(URL_BASE, str(Path(__file__).parent), False)]
            )
            _LOGGER.debug("Chemin enregistré : %s", URL_BASE)
        except (RuntimeError, ValueError):
            _LOGGER.debug("Chemin déjà enregistré : %s", URL_BASE)

    async def _async_wait_for_lovelace_resources(self) -> None:
        """Attend que la collection de ressources soit chargée."""
        attempts = 0

        async def _check_loaded(_now: Any) -> None:
            nonlocal attempts
            if self.lovelace.resources.loaded:
                await self._async_register_modules()
                return
            attempts += 1
            if attempts >= MAX_ATTEMPTS:
                _LOGGER.warning(
                    "Ressources Lovelace toujours indisponibles : ajoutez la "
                    "ressource à la main (%s/%s, type module)",
                    URL_BASE,
                    CARD_FILENAME,
                )
                return
            _LOGGER.debug("Ressources Lovelace non chargées, nouvel essai dans %ss", RETRY_DELAY)
            async_call_later(self.hass, RETRY_DELAY, _check_loaded)

        await _check_loaded(0)

    async def _async_register_modules(self) -> None:
        """Crée la ressource si elle manque, sans paramètre de version.

        Un `?v=` dans l'URL ne règle de toute façon pas le cache de l'app
        mobile : c'est la commande websocket `birdnet/version` qui s'en charge.
        """
        existing = [
            resource
            for resource in self.lovelace.resources.async_items()
            if str(resource.get("url", "")).startswith(URL_BASE)
        ]

        for module in JSMODULES:
            url = f"{URL_BASE}/{module['filename']}"
            registered = False

            for resource in existing:
                if self._get_path(resource["url"]) != url:
                    continue
                registered = True
                if resource["url"] != url:
                    # Nettoie un ?v= hérité d'une version précédente.
                    _LOGGER.info("Ressource %s : suppression du suffixe de version", url)
                    await self.lovelace.resources.async_update_item(
                        resource["id"], {"res_type": "module", "url": url}
                    )
                break

            if not registered:
                _LOGGER.info("Enregistrement de %s (%s)", module["name"], url)
                await self.lovelace.resources.async_create_item(
                    {"res_type": "module", "url": url}
                )

    async def async_unregister(self) -> None:
        """Retire les ressources lors de la suppression de l'intégration."""
        if self._mode != "storage":
            return
        for module in JSMODULES:
            url = f"{URL_BASE}/{module['filename']}"
            for resource in [
                item
                for item in self.lovelace.resources.async_items()
                if str(item.get("url", "")).startswith(url)
            ]:
                await self.lovelace.resources.async_delete_item(resource["id"])

    @staticmethod
    def _get_path(url: str) -> str:
        """Chemin sans les paramètres de requête."""
        return url.split("?")[0]
