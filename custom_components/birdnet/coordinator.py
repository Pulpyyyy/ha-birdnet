"""Collection of the BirdNET detections published over MQTT."""

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
    CONF_BASE_URL,
    CONF_CLIP_SECRET,
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
from .http import clip_path
from .models import Detection

_LOGGER = logging.getLogger(__name__)

type BirdNetConfigEntry = ConfigEntry[BirdNetCoordinator]


class BirdNetCoordinator:
    """Holds the latest detection and the log for the day."""

    def __init__(self, hass: HomeAssistant, entry: BirdNetConfigEntry) -> None:
        """Initialise the collector."""
        self.hass = hass
        self.entry = entry
        self.last_detection: Detection | None = None
        self.detections: list[Detection] = []
        self.last_error: str | None = None
        self.messages_received = 0
        self.duplicates_ignored = 0
        self._seen: set[str] = set()
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
        """MQTT topic being listened to."""
        return self.entry.options.get(
            CONF_TOPIC, self.entry.data.get(CONF_TOPIC, DEFAULT_TOPIC)
        )

    @property
    def min_confidence(self) -> float:
        """Minimum confidence, as a percentage."""
        return float(
            self.entry.options.get(
                CONF_MIN_CONFIDENCE,
                self.entry.data.get(CONF_MIN_CONFIDENCE, DEFAULT_MIN_CONFIDENCE),
            )
        )

    @property
    def excluded_species(self) -> list[str]:
        """Ignored species (case-insensitive comparison)."""
        raw = self.entry.options.get(
            CONF_EXCLUDED_SPECIES, self.entry.data.get(CONF_EXCLUDED_SPECIES, [])
        )
        if isinstance(raw, str):
            raw = [part.strip() for part in raw.split(",")]
        return [item.lower() for item in raw if item]

    @property
    def base_url(self) -> str | None:
        """Address of the BirdNET instance, without a trailing slash."""
        raw = self.entry.options.get(
            CONF_BASE_URL, self.entry.data.get(CONF_BASE_URL, "")
        )
        return str(raw).strip().rstrip("/") or None

    @property
    def max_detections(self) -> int:
        """Maximum number of detections kept for the day."""
        return int(
            self.entry.options.get(CONF_MAX_DETECTIONS, DEFAULT_MAX_DETECTIONS)
        )

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------
    async def async_setup(self) -> None:
        """Load the history, subscribe to the topic and schedule the reset."""
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
        _LOGGER.debug("Subscribed to BirdNET topic %s", self.topic)

    async def async_shutdown(self) -> None:
        """Cancel the subscriptions and save the state."""
        for unsub in self._unsubs:
            unsub()
        self._unsubs.clear()
        await self._async_save()

    @callback
    def async_add_listener(self, listener: Callable[[], None]) -> Callable[[], None]:
        """Register an entity to notify on every change."""
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
    # Persistence
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
        self._seen = {self._dedup_key(item) for item in self.detections}
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
        """Handle a message received on the BirdNET topic."""
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
            # Some setups simply publish the species name.
            data = {"common_name": payload}

        if not isinstance(data, dict):
            self.last_error = f"Unexpected payload on {msg.topic}"
            _LOGGER.warning("%s: %s", self.last_error, payload[:200])
            return

        detection = Detection.from_payload(data)
        if detection is None:
            self.last_error = f"No species found in the payload from {msg.topic}"
            _LOGGER.warning("%s: %s", self.last_error, payload[:200])
            return

        self.last_error = None

        names = {
            (detection.common_name or "").lower(),
            (detection.scientific_name or "").lower(),
        }
        if names & set(self.excluded_species):
            _LOGGER.debug("Detection ignored (excluded): %s", detection.common_name)
            return

        if (
            detection.confidence is not None
            and detection.confidence * 100 < self.min_confidence
        ):
            _LOGGER.debug(
                "Detection ignored (%s %.0f%% < %.0f%%)",
                detection.common_name,
                detection.confidence * 100,
                self.min_confidence,
            )
            return

        self.async_add_detection(detection)

    @staticmethod
    def _dedup_key(detection: Detection) -> str:
        """Identity of a detection, for the duplicate check."""
        return f"{detection.detected_at.isoformat()}|{detection.common_name.lower()}"

    @callback
    def async_add_detection(self, detection: Detection) -> None:
        """Store an accepted detection and notify the entities."""
        # BirdNET analyses overlapping windows, so the same detection can be
        # published several times with the exact same timestamp. Counting it
        # twice would inflate the daily figures. Timestamps have a one second
        # resolution, and one species cannot be heard twice within one second.
        key = self._dedup_key(detection)
        if key in self._seen:
            self.duplicates_ignored += 1
            _LOGGER.debug(
                "Duplicate ignored: %s at %s",
                detection.common_name,
                detection.detected_at,
            )
            return

        if detection.detected_at < dt_util.start_of_local_day():
            # Yesterday's detection (a retained message picked up at startup):
            # keep it as the last known one without polluting today's log.
            self.last_detection = self.last_detection or detection
            self._notify()
            return

        self.last_detection = detection
        self.detections.append(detection)
        self._seen.add(key)
        if len(self.detections) > self.max_detections:
            dropped = self.detections[: len(self.detections) - self.max_detections]
            del self.detections[: len(dropped)]
            self._seen.difference_update(self._dedup_key(item) for item in dropped)

        self._store.async_delay_save(self._data_to_save, 30)
        self._notify()

    @callback
    def _handle_midnight(self, _now: Any) -> None:
        """Clear the daily log at midnight."""
        self.async_clear_log()

    @callback
    def async_clear_log(self) -> None:
        """Clear today's log without touching the latest detection."""
        self.detections = []
        self._seen.clear()
        self._store.async_delay_save(self._data_to_save, 5)
        self._notify()

    # ------------------------------------------------------------------
    # Aggregates
    # ------------------------------------------------------------------
    @callback
    def species_summary(self) -> list[dict[str, Any]]:
        """Per-species summary, most recently heard first."""
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
            # One message without a scientific name must not deprive the species
            # of its own for the rest of the day.
            if detection.scientific_name and not entry["scientific_name"]:
                entry["scientific_name"] = detection.scientific_name
            if detection.detected_at.isoformat() >= entry["last_timestamp"]:
                entry["last_time"] = detection.detected_at.strftime("%H:%M:%S")
                entry["last_timestamp"] = detection.detected_at.isoformat()
                entry["scientific_name"] = (
                    detection.scientific_name or entry["scientific_name"]
                )
                entry["image"] = detection.image_url or entry["image"]
                entry["link"] = detection.link or entry["link"]
        return sorted(
            summary.values(), key=lambda item: item["last_timestamp"], reverse=True
        )

    @callback
    def detections_as_dicts(self) -> list[dict[str, Any]]:
        """Today's log, most recent first."""
        return [self.detection_as_dict(item) for item in reversed(self.detections)]

    # ------------------------------------------------------------------
    # Audio clips
    # ------------------------------------------------------------------
    @callback
    def clip_proxy_url(self, url: str | None) -> str | None:
        """Equivalent local URL, served by Home Assistant.

        Required as soon as Home Assistant is reached over HTTPS or from
        outside: the private address of BirdNET is then not reachable by the
        browser.
        """
        if not url:
            return None
        if not (secret := self.entry.data.get(CONF_CLIP_SECRET)):
            return None
        return clip_path(secret, self.entry.entry_id, url)

    @callback
    def audio_source(self, detection: Detection) -> str | None:
        """Direct URL of the clip, whichever BirdNET published the detection.

        BirdNET-Pi announces its own address in the listen link, from which the
        clip path is rebuilt. BirdNET-Go publishes no address at all, but gives
        a detection id: its API serves the clip at /api/v2/audio/<id>, so the
        instance URL has to be configured.
        """
        if detection.detection_id and (base := self.base_url):
            return f"{base}/api/v2/audio/{detection.detection_id}"
        return detection.audio_url

    @callback
    def detection_as_dict(self, detection: Detection) -> dict[str, Any]:
        """Detection exposed to the entities, relayed audio clip included."""
        data = detection.as_dict()
        source = self.audio_source(detection)
        data["audio"] = source
        if proxied := self.clip_proxy_url(source):
            data["audio"] = proxied
            data["audio_source"] = source
        return data
