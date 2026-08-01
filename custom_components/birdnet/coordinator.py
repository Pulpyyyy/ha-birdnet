"""Collecte des détections BirdNET publiées sur MQTT."""

from __future__ import annotations

from collections.abc import Callable
import json
import logging
from typing import Any

from homeassistant.components import mqtt
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.event import async_track_time_change
from homeassistant.helpers.storage import Store
from homeassistant.util import dt as dt_util

from .const import (
    CONF_EXCLUDED_SPECIES,
    CONF_MAX_DETECTIONS,
    CONF_MIN_CONFIDENCE,
    CONF_TOPIC,
    DEFAULT_MAX_DETECTIONS,
    DEFAULT_MIN_CONFIDENCE,
    DEFAULT_TOPIC,
    STORAGE_KEY,
    STORAGE_VERSION,
)
from .models import Detection

_LOGGER = logging.getLogger(__name__)

type BirdNetConfigEntry = ConfigEntry[BirdNetCoordinator]


class BirdNetCoordinator:
    """Garde en mémoire la dernière détection et le journal du jour."""

    def __init__(self, hass: HomeAssistant, entry: BirdNetConfigEntry) -> None:
        """Initialise le collecteur."""
        self.hass = hass
        self.entry = entry
        self.last_detection: Detection | None = None
        self.detections: list[Detection] = []
        self.last_error: str | None = None
        self.messages_received = 0
        self._listeners: list[Callable[[], None]] = []
        self._unsubs: list[Callable[[], None]] = []
        self._store: Store[dict[str, Any]] = Store(
            hass, STORAGE_VERSION, f"{STORAGE_KEY}.{entry.entry_id}"
        )

    # ------------------------------------------------------------------
    # Options
    # ------------------------------------------------------------------
    @property
    def topic(self) -> str:
        """Topic MQTT écouté."""
        return self.entry.options.get(
            CONF_TOPIC, self.entry.data.get(CONF_TOPIC, DEFAULT_TOPIC)
        )

    @property
    def min_confidence(self) -> float:
        """Confiance minimale, en pourcentage."""
        return float(
            self.entry.options.get(
                CONF_MIN_CONFIDENCE,
                self.entry.data.get(CONF_MIN_CONFIDENCE, DEFAULT_MIN_CONFIDENCE),
            )
        )

    @property
    def excluded_species(self) -> list[str]:
        """Espèces ignorées (comparaison insensible à la casse)."""
        raw = self.entry.options.get(
            CONF_EXCLUDED_SPECIES, self.entry.data.get(CONF_EXCLUDED_SPECIES, [])
        )
        if isinstance(raw, str):
            raw = [part.strip() for part in raw.split(",")]
        return [item.lower() for item in raw if item]

    @property
    def max_detections(self) -> int:
        """Nombre maximal de détections conservées pour la journée."""
        return int(
            self.entry.options.get(CONF_MAX_DETECTIONS, DEFAULT_MAX_DETECTIONS)
        )

    # ------------------------------------------------------------------
    # Cycle de vie
    # ------------------------------------------------------------------
    async def async_setup(self) -> None:
        """Charge l'historique, s'abonne au topic et programme le reset."""
        await self._async_load()

        self._unsubs.append(
            await mqtt.async_subscribe(
                self.hass, self.topic, self._handle_message, encoding="utf-8"
            )
        )
        self._unsubs.append(
            async_track_time_change(
                self.hass, self._handle_midnight, hour=0, minute=0, second=0
            )
        )
        _LOGGER.debug("Abonné au topic BirdNET %s", self.topic)

    async def async_shutdown(self) -> None:
        """Coupe les abonnements et sauvegarde l'état."""
        for unsub in self._unsubs:
            unsub()
        self._unsubs.clear()
        await self._async_save()

    @callback
    def async_add_listener(self, listener: Callable[[], None]) -> Callable[[], None]:
        """Enregistre une entité à notifier à chaque changement."""
        self._listeners.append(listener)

        @callback
        def _remove() -> None:
            self._listeners.remove(listener)

        return _remove

    @callback
    def _notify(self) -> None:
        for listener in list(self._listeners):
            listener()

    # ------------------------------------------------------------------
    # Persistance
    # ------------------------------------------------------------------
    async def _async_load(self) -> None:
        data = await self._store.async_load()
        if not data:
            return
        today = dt_util.start_of_local_day()
        restored = [
            detection
            for raw in data.get("detections", [])
            if (detection := Detection.from_store(raw)) is not None
            and detection.detected_at >= today
        ]
        self.detections = restored[-self.max_detections :]
        if last := data.get("last_detection"):
            self.last_detection = Detection.from_store(last)

    async def _async_save(self) -> None:
        await self._store.async_save(self._data_to_save())

    @callback
    def _data_to_save(self) -> dict[str, Any]:
        return {
            "detections": [item.to_store() for item in self.detections],
            "last_detection": (
                self.last_detection.to_store() if self.last_detection else None
            ),
        }

    # ------------------------------------------------------------------
    # MQTT
    # ------------------------------------------------------------------
    @callback
    def _handle_message(self, msg: mqtt.ReceiveMessage) -> None:
        """Traite un message reçu sur le topic BirdNET."""
        self.messages_received += 1
        payload = msg.payload
        if isinstance(payload, bytes):
            payload = payload.decode("utf-8", errors="replace")
        payload = payload.strip()
        if not payload:
            return

        try:
            data = json.loads(payload)
        except ValueError:
            # Certaines configurations publient simplement le nom de l'espèce.
            data = {"common_name": payload}

        if not isinstance(data, dict):
            self.last_error = f"Payload inattendu sur {msg.topic}"
            _LOGGER.warning("%s : %s", self.last_error, payload[:200])
            return

        detection = Detection.from_payload(data)
        if detection is None:
            self.last_error = f"Aucune espèce trouvée dans le payload de {msg.topic}"
            _LOGGER.warning("%s : %s", self.last_error, payload[:200])
            return

        self.last_error = None

        names = {
            (detection.common_name or "").lower(),
            (detection.scientific_name or "").lower(),
        }
        if names & set(self.excluded_species):
            _LOGGER.debug("Détection ignorée (exclusion) : %s", detection.common_name)
            return

        if (
            detection.confidence is not None
            and detection.confidence * 100 < self.min_confidence
        ):
            _LOGGER.debug(
                "Détection ignorée (%s %.0f%% < %.0f%%)",
                detection.common_name,
                detection.confidence * 100,
                self.min_confidence,
            )
            return

        self.async_add_detection(detection)

    @callback
    def async_add_detection(self, detection: Detection) -> None:
        """Ajoute une détection retenue et prévient les entités."""
        if detection.detected_at < dt_util.start_of_local_day():
            # Détection de la veille (message retenu au démarrage) : on garde
            # la dernière connue sans polluer le journal du jour.
            self.last_detection = self.last_detection or detection
            self._notify()
            return

        self.last_detection = detection
        self.detections.append(detection)
        if len(self.detections) > self.max_detections:
            del self.detections[: len(self.detections) - self.max_detections]

        self._store.async_delay_save(self._data_to_save, 30)
        self._notify()

    @callback
    def _handle_midnight(self, _now: Any) -> None:
        """Vide le journal quotidien à minuit."""
        self.async_clear_log()

    @callback
    def async_clear_log(self) -> None:
        """Vide le journal du jour sans toucher à la dernière détection."""
        self.detections = []
        self._store.async_delay_save(self._data_to_save, 5)
        self._notify()

    # ------------------------------------------------------------------
    # Agrégats
    # ------------------------------------------------------------------
    @callback
    def species_summary(self) -> list[dict[str, Any]]:
        """Résumé par espèce, la plus récemment entendue en premier."""
        summary: dict[str, dict[str, Any]] = {}
        for detection in self.detections:
            key = detection.common_name.lower()
            entry = summary.get(key)
            confidence = detection.confidence_pct
            if entry is None:
                summary[key] = {
                    "name": detection.common_name,
                    "scientific_name": detection.scientific_name,
                    "count": 1,
                    "max_confidence": confidence,
                    "last_time": detection.detected_at.strftime("%H:%M:%S"),
                    "last_timestamp": detection.detected_at.isoformat(),
                    "image": detection.image_url,
                    "link": detection.link,
                }
                continue
            entry["count"] += 1
            if confidence is not None and (
                entry["max_confidence"] is None or confidence > entry["max_confidence"]
            ):
                entry["max_confidence"] = confidence
            if detection.detected_at.isoformat() >= entry["last_timestamp"]:
                entry["last_time"] = detection.detected_at.strftime("%H:%M:%S")
                entry["last_timestamp"] = detection.detected_at.isoformat()
                entry["image"] = detection.image_url or entry["image"]
                entry["link"] = detection.link or entry["link"]
        return sorted(
            summary.values(), key=lambda item: item["last_timestamp"], reverse=True
        )

    @callback
    def detections_as_dicts(self) -> list[dict[str, Any]]:
        """Journal du jour, du plus récent au plus ancien."""
        return [item.as_dict() for item in reversed(self.detections)]
