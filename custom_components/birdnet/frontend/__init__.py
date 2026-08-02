"""Registration of the Lovelace card shipped with the integration.

Structure and sequence taken from KipK's developer guide on embedding a Lovelace
card in a Home Assistant integration (https://forum.hacf.fr/t/74074): the static
path is always registered, the resource is only added in storage mode, and the
Lovelace resources are given time to load before being touched.
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
    """Publishes the JavaScript modules of the integration."""

    def __init__(self, hass: HomeAssistant) -> None:
        """Initialise the registrar."""
        self.hass = hass
        self.lovelace = hass.data.get("lovelace")

    @property
    def _mode(self) -> str:
        """Lovelace mode: storage or yaml."""
        return getattr(
            self.lovelace, "mode", getattr(self.lovelace, "resource_mode", "yaml")
        )

    async def async_register(self) -> None:
        """Serve the files, then reference the modules in Lovelace."""
        await self._async_register_path()

        if self._mode != "storage":
            _LOGGER.info(
                "Lovelace in YAML mode: add the resource by hand -> "
                "url: %s/%s , type: module",
                URL_BASE,
                CARD_FILENAME,
            )
            return

        await self._async_wait_for_lovelace_resources()

    async def _async_register_path(self) -> None:
        """Register the static HTTP path serving the frontend folder."""
        try:
            await self.hass.http.async_register_static_paths(
                [StaticPathConfig(URL_BASE, str(Path(__file__).parent), False)]
            )
            _LOGGER.debug("Path registered: %s", URL_BASE)
        except (RuntimeError, ValueError):
            _LOGGER.debug("Path already registered: %s", URL_BASE)

    async def _async_wait_for_lovelace_resources(self) -> None:
        """Wait for the resource collection to be loaded."""
        attempts = 0

        async def _check_loaded(_now: Any) -> None:
            nonlocal attempts
            if self.lovelace.resources.loaded:
                await self._async_register_modules()
                return
            attempts += 1
            if attempts >= MAX_ATTEMPTS:
                _LOGGER.warning(
                    "Lovelace resources still unavailable: add the resource by "
                    "hand (%s/%s, type module)",
                    URL_BASE,
                    CARD_FILENAME,
                )
                return
            _LOGGER.debug("Lovelace resources not loaded, retrying in %ss", RETRY_DELAY)
            async_call_later(self.hass, RETRY_DELAY, _check_loaded)

        await _check_loaded(0)

    async def _async_register_modules(self) -> None:
        """Create the resource when missing, without a version parameter.

        A `?v=` in the URL does not fix the companion app cache anyway: the
        `birdnet/version` websocket command takes care of that.
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
                    # Clean up a `?v=` inherited from an earlier version.
                    _LOGGER.info("Resource %s: dropping the version suffix", url)
                    await self.lovelace.resources.async_update_item(
                        resource["id"], {"res_type": "module", "url": url}
                    )
                break

            if not registered:
                _LOGGER.info("Registering %s (%s)", module["name"], url)
                await self.lovelace.resources.async_create_item(
                    {"res_type": "module", "url": url}
                )

    async def async_unregister(self) -> None:
        """Remove the resources when the integration is deleted."""
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
        """Path without the query parameters."""
        return url.split("?")[0]
