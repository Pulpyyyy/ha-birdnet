"""Relais des extraits audio BirdNET à travers Home Assistant.

Le lecteur de la carte télécharge le clip depuis le navigateur. Or BirdNET-Pi
n'est souvent joignable qu'en `http://` sur une IP privée : depuis l'extérieur
l'adresse est inatteignable, et derrière un Home Assistant en HTTPS le
navigateur bloque la requête (contenu mixte).

Home Assistant, lui, est sur le même réseau que BirdNET. Il sert donc de relais :
la carte demande le clip à Home Assistant, qui va le chercher et le renvoie sur
sa propre origine.

L'URL distante voyage en clair dans la requête, accompagnée d'une signature
HMAC calculée avec un secret propre à l'entrée de configuration. Sans cette
signature la vue refuse de récupérer quoi que ce soit, ce qui interdit de s'en
servir pour sonder le réseau.
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
    """Signature courte de l'URL distante."""
    return hmac.new(secret.encode(), url.encode(), sha256).hexdigest()[:32]


def clip_path(secret: str, entry_id: str, url: str) -> str:
    """URL locale à publier dans les attributs pour un clip distant."""
    return f"{CLIP_URL}/{entry_id}/{_sign(secret, url)}?url={quote(url, safe='')}"


def async_register_clip_view(hass: HomeAssistant) -> None:
    """Enregistre la vue une seule fois."""
    if hass.data.get(_VIEW_REGISTERED):
        return
    hass.data[_VIEW_REGISTERED] = True
    hass.http.register_view(BirdNetClipView())


class BirdNetClipView(HomeAssistantView):
    """Renvoie un extrait audio BirdNET depuis l'origine de Home Assistant."""

    url = CLIP_URL + "/{entry_id}/{signature}"
    name = "api:birdnet:clip"
    # Une balise <audio> ne peut pas porter d'en-tête d'authentification ; c'est
    # la signature qui protège la vue.
    requires_auth = False

    async def get(
        self, request: web.Request, entry_id: str, signature: str
    ) -> web.StreamResponse:
        """Relaie le clip demandé."""
        hass: HomeAssistant = request.app[KEY_HASS]

        target = request.query.get("url", "")
        entry = hass.config_entries.async_get_entry(entry_id)
        secret = entry.data.get(CONF_CLIP_SECRET) if entry else None
        if not secret or not target:
            return web.Response(status=404)

        if not hmac.compare_digest(signature, _sign(secret, target)):
            _LOGGER.warning("Signature invalide pour un extrait BirdNET")
            return web.Response(status=403)

        if urlparse(target).scheme not in ("http", "https"):
            return web.Response(status=400)

        session = async_get_clientsession(hass)
        try:
            async with session.get(target, timeout=_TIMEOUT) as upstream:
                if upstream.status != 200:
                    _LOGGER.debug(
                        "BirdNET a répondu %s pour %s", upstream.status, target
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
            _LOGGER.warning("Extrait BirdNET injoignable (%s) : %s", target, err)
            return web.Response(status=502)
