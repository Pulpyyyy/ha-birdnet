"""Normalisation of the BirdNET payloads received over MQTT.

The goal is to accept any of these interchangeably:

* BirdNET-Pi through Apprise (snake_case keys, values always strings) ::

      {"common_name": "Eurasian Magpie", "scientific_name": "Pica pica",
       "confidence_score": "0.9871", "link": "http://.../?filename=x.mp3",
       "date": "2026-08-01", "time": "22:06:15", "image": "https://..."}

* BirdNET-Go (PascalCase keys, nested ``BirdImage``) ::

      {"CommonName": "Eurasian Magpie", "ScientificName": "Pica pica",
       "Confidence": 0.9871, "Date": "2026-08-01", "Time": "22:06:15",
       "BirdImage": {"URL": "https://..."}}

* the home-made scripts from community tutorials (``common_name`` with an ISO
  ``timestamp``).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
import re
from typing import Any
from urllib.parse import parse_qs, urlparse

from homeassistant.util import dt as dt_util

# Key aliases, once the key has been flattened (lowercase, no _ or -).
_ALIASES: dict[str, tuple[str, ...]] = {
    "common_name": ("commonname", "comname", "species", "birdname", "name"),
    "scientific_name": ("scientificname", "sciname", "latinname", "scientific"),
    "confidence": ("confidencescore", "confidence", "score"),
    "image": ("image", "imageurl", "flickrimage", "birdimage", "picture", "thumbnail"),
    "link": ("link", "listenurl", "clipurl", "detectionurl", "url"),
    "audio": ("audiourl", "audio", "clipname", "mp3"),
    "date": ("date",),
    "time": ("time",),
    # "begintime" is deliberately absent: BirdNET-Go publishes it as the start
    # of the analysis window, up to 20 seconds before the detection itself. Its
    # own API reports Date + Time as the detection timestamp.
    "timestamp": ("timestamp", "datetime"),
    "detection_id": ("detectionid",),
    "latitude": ("latitude", "lat"),
    "longitude": ("longitude", "lon", "lng"),
    "species_code": ("speciescode", "code"),
    "source": ("sourcenode", "source", "station"),
}

# BirdNET-Pi file name: Eurasian_Magpie-99-2026-08-01-birdnet-22:06:15.mp3
_RE_PI_FILENAME = re.compile(r"^(?P<name>.+?)-\d+-\d{4}-\d{2}-\d{2}-")


def _flatten_key(key: str) -> str:
    return key.lower().replace("_", "").replace("-", "").replace(" ", "")


def _pick(payload: dict[str, Any], target: str) -> Any:
    """Return the first payload value matching a known alias."""
    flat = {_flatten_key(k): v for k, v in payload.items()}
    for alias in _ALIASES[target]:
        if alias in flat:
            value = flat[alias]
            if value not in (None, "", "None"):
                return value
    return None


def _as_url(value: Any) -> str | None:
    """Extract a URL, including from a nested object (BirdNET-Go)."""
    if isinstance(value, dict):
        for key in ("URL", "url", "Url"):
            if url := value.get(key):
                return str(url)
        return None
    if isinstance(value, str) and value.startswith(("http://", "https://", "/")):
        return value
    return None


def _as_float(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    try:
        return float(str(value).strip().rstrip("%").replace(",", "."))
    except (TypeError, ValueError):
        return None


def _as_confidence(value: Any) -> float | None:
    """Bring a confidence back into the 0..1 range.

    Accepts 0.9871, "0.9871", "98.71%" or 99.
    """
    number = _as_float(value)
    if number is None:
        return None
    if isinstance(value, str) and value.strip().endswith("%"):
        number /= 100
    elif number > 1:
        number /= 100
    return max(0.0, min(1.0, number))


def _parse_datetime(payload: dict[str, Any]) -> datetime:
    """Rebuild the local timestamp of the detection."""
    if raw := _pick(payload, "timestamp"):
        if parsed := dt_util.parse_datetime(str(raw)):
            return dt_util.as_local(
                parsed if parsed.tzinfo else parsed.replace(tzinfo=dt_util.DEFAULT_TIME_ZONE)
            )

    date_raw = _pick(payload, "date")
    time_raw = _pick(payload, "time")
    if date_raw and time_raw:
        if parsed := dt_util.parse_datetime(f"{date_raw} {time_raw}"):
            return dt_util.as_local(
                parsed if parsed.tzinfo else parsed.replace(tzinfo=dt_util.DEFAULT_TIME_ZONE)
            )
    if time_raw and (parsed_time := dt_util.parse_time(str(time_raw))):
        return dt_util.start_of_local_day().replace(
            hour=parsed_time.hour,
            minute=parsed_time.minute,
            second=parsed_time.second,
        )
    return dt_util.now()


def _derive_audio_url(link: str | None, common_name: str, moment: datetime) -> str | None:
    """Rebuild the BirdNET-Pi audio clip URL from the listen link.

    ``http://birdnet-pi/?filename=Eurasian_Magpie-99-2026-08-01-birdnet-22:06:15.mp3``
    becomes ``http://birdnet-pi/By_Date/2026-08-01/Eurasian_Magpie/<filename>``.
    """
    if not link:
        return None
    parsed = urlparse(link)
    # Match on the path only: the BirdNET-Pi listen link also ends in ".mp3",
    # but inside its query string ("?filename=x.mp3"). Testing the whole URL
    # would mistake that HTML page for the clip itself.
    if parsed.path.lower().endswith((".mp3", ".wav", ".flac", ".ogg")):
        return link
    filenames = parse_qs(parsed.query).get("filename")
    if not filenames:
        return None
    filename = filenames[0]
    # The folder is named after the common name, as it appears at the head of
    # the file name.
    match = _RE_PI_FILENAME.match(filename)
    folder = match.group("name") if match else common_name.replace(" ", "_")
    base = f"{parsed.scheme}://{parsed.netloc}"
    return f"{base}/By_Date/{moment.strftime('%Y-%m-%d')}/{folder}/{filename}"


@dataclass(slots=True)
class Detection:
    """A normalised detection."""

    common_name: str
    scientific_name: str | None = None
    confidence: float | None = None
    image_url: str | None = None
    link: str | None = None
    audio_url: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    species_code: str | None = None
    source: str | None = None
    # BirdNET-Go only: database id, the key to its audio API.
    detection_id: str | None = None
    detected_at: datetime = field(default_factory=dt_util.now)

    @classmethod
    def from_payload(cls, payload: dict[str, Any]) -> Detection | None:
        """Build a detection from a decoded MQTT payload."""
        common_name = _pick(payload, "common_name")
        scientific_name = _pick(payload, "scientific_name")
        if not common_name and not scientific_name:
            return None

        detected_at = _parse_datetime(payload)
        name = str(common_name or scientific_name).strip()
        link = _as_url(_pick(payload, "link"))
        audio_url = _as_url(_pick(payload, "audio")) or _derive_audio_url(
            link, name, detected_at
        )

        return cls(
            common_name=name,
            scientific_name=str(scientific_name).strip() if scientific_name else None,
            confidence=_as_confidence(_pick(payload, "confidence")),
            image_url=_as_url(_pick(payload, "image")),
            link=link,
            audio_url=audio_url,
            latitude=_as_float(_pick(payload, "latitude")),
            longitude=_as_float(_pick(payload, "longitude")),
            species_code=(
                str(code) if (code := _pick(payload, "species_code")) else None
            ),
            source=str(src) if (src := _pick(payload, "source")) else None,
            detection_id=(
                str(ident) if (ident := _pick(payload, "detection_id")) else None
            ),
            detected_at=detected_at,
        )

    @property
    def confidence_pct(self) -> float | None:
        """Confidence as a percentage, rounded to the nearest integer."""
        if self.confidence is None:
            return None
        return round(self.confidence * 100)

    def as_dict(self) -> dict[str, Any]:
        """Representation exposed in the entity attributes and to the card."""
        return {
            "name": self.common_name,
            "common_name": self.common_name,
            "scientific_name": self.scientific_name,
            "confidence": self.confidence_pct,
            "confidence_score": self.confidence,
            "time": self.detected_at.strftime("%H:%M:%S"),
            "date": self.detected_at.strftime("%Y-%m-%d"),
            "timestamp": self.detected_at.isoformat(),
            "image": self.image_url,
            "link": self.link,
            "audio": self.audio_url,
            "species_code": self.species_code,
            "detection_id": self.detection_id,
        }

    def to_store(self) -> dict[str, Any]:
        """Representation persisted to disk."""
        return {
            "common_name": self.common_name,
            "scientific_name": self.scientific_name,
            "confidence": self.confidence,
            "image_url": self.image_url,
            "link": self.link,
            "audio_url": self.audio_url,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "species_code": self.species_code,
            "source": self.source,
            "detection_id": self.detection_id,
            "detected_at": self.detected_at.isoformat(),
        }

    @classmethod
    def from_store(cls, data: dict[str, Any]) -> Detection | None:
        """Read back a persisted detection; skip corrupted entries."""
        try:
            detected_at = dt_util.parse_datetime(data["detected_at"])
            if detected_at is None:
                return None
            return cls(
                common_name=data["common_name"],
                scientific_name=data.get("scientific_name"),
                confidence=data.get("confidence"),
                image_url=data.get("image_url"),
                link=data.get("link"),
                audio_url=data.get("audio_url"),
                latitude=data.get("latitude"),
                longitude=data.get("longitude"),
                species_code=data.get("species_code"),
                source=data.get("source"),
                detection_id=data.get("detection_id"),
                detected_at=dt_util.as_local(detected_at),
            )
        except (KeyError, TypeError, ValueError):
            return None
