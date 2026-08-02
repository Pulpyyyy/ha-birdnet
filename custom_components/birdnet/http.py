"""Relaying of the BirdNET audio clips through Home Assistant.

The card player downloads the clip from the browser. BirdNET-Pi, however, is
often reachable only over plain ``http://`` on a private address: from outside
the network the address cannot be reached at all, and behind a Home Assistant
served over HTTPS the browser blocks the request as mixed content.

Home Assistant, on the other hand, sits on the same network as BirdNET. It acts
as a relay: the card asks Home Assistant for the clip, which fetches it and
returns it on its own origin.

The remote URL travels in clear in the request, together with an HMAC signature
computed with a secret specific to the config entry. Without that signature the
view refuses to fetch anything, which prevents it from being used to probe the
network.
"""

from __future__ import annotations

from hashlib import sha256
import hmac
import logging
from urllib.parse import quote, urlparse

from aiohttp import ClientError, ClientTimeout, web
from homeassistant.components.http import KEY_HASS, HomeAssistantView
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import CONF_CLIP_SECRET, DOMAIN

_LOGGER = logging.getLogger(__name__)

CLIP_URL = "/api/birdnet/clip"
_TIMEOUT = ClientTimeout(total=30, connect=5)
_CHUNK = 64 * 1024

_VIEW_REGISTERED = f"{DOMAIN}_clip_view"


def _sign(secret: str, url: str) -> str:
    """Short signature of the remote URL."""
    return hmac.new(secret.encode(), url.encode(), sha256).hexdigest()[:32]


def clip_path(secret: str, entry_id: str, url: str) -> str:
    """Local URL to publish in the attributes for a remote clip."""
    return f"{CLIP_URL}/{entry_id}/{_sign(secret, url)}?url={quote(url, safe='')}"


def async_register_clip_view(hass: HomeAssistant) -> None:
    """Register the view once."""
    if hass.data.get(_VIEW_REGISTERED):
        return
    hass.data[_VIEW_REGISTERED] = True
    hass.http.register_view(BirdNetClipView())


class BirdNetClipView(HomeAssistantView):
    """Return a BirdNET audio clip from the Home Assistant origin."""

    url = CLIP_URL + "/{entry_id}/{signature}"
    name = "api:birdnet:clip"
    # An <audio> tag cannot carry an authentication header; the signature is
    # what protects the view.
    requires_auth = False

    async def get(
        self, request: web.Request, entry_id: str, signature: str
    ) -> web.StreamResponse:
        """Relay the requested clip."""
        hass: HomeAssistant = request.app[KEY_HASS]

        target = request.query.get("url", "")
        entry = hass.config_entries.async_get_entry(entry_id)
        secret = entry.data.get(CONF_CLIP_SECRET) if entry else None
        if not secret or not target:
            return web.Response(status=404)

        if not hmac.compare_digest(signature, _sign(secret, target)):
            _LOGGER.warning("Invalid signature for a BirdNET clip")
            return web.Response(status=403)

        if urlparse(target).scheme not in ("http", "https"):
            return web.Response(status=400)

        session = async_get_clientsession(hass)
        try:
            async with session.get(target, timeout=_TIMEOUT) as upstream:
                if upstream.status != 200:
                    _LOGGER.debug(
                        "BirdNET answered %s for %s", upstream.status, target
                    )
                    return web.Response(status=upstream.status)

                headers = {
                    "Content-Type": upstream.headers.get("Content-Type", "audio/mpeg"),
                    "Cache-Control": "private, max-age=3600",
                }
                if length := upstream.headers.get("Content-Length"):
                    headers["Content-Length"] = length

                response = web.StreamResponse(status=200, headers=headers)
                await response.prepare(request)
                async for chunk in upstream.content.iter_chunked(_CHUNK):
                    await response.write(chunk)
                await response.write_eof()
                return response
        except (ClientError, TimeoutError) as err:
            _LOGGER.warning("BirdNET clip unreachable (%s): %s", target, err)
            return web.Response(status=502)
