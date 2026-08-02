"""Constants for the BirdNET integration."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Final

DOMAIN: Final = "birdnet"

# The version is the reference for the card-side version check.
MANIFEST_PATH: Final = Path(__file__).parent / "manifest.json"
with MANIFEST_PATH.open(encoding="utf-8") as manifest_file:
    INTEGRATION_VERSION: Final[str] = json.load(manifest_file).get("version", "0.0.0")

# Configuration
CONF_TOPIC: Final = "topic"
CONF_MIN_CONFIDENCE: Final = "min_confidence"
CONF_EXCLUDED_SPECIES: Final = "excluded_species"
CONF_MAX_DETECTIONS: Final = "max_detections"
# Per-entry secret, used to sign the URLs of relayed audio clips.
CONF_CLIP_SECRET: Final = "clip_secret"

DEFAULT_TOPIC: Final = "birdnet/detection"
DEFAULT_MIN_CONFIDENCE: Final = 70
DEFAULT_MAX_DETECTIONS: Final = 500
DEFAULT_NAME: Final = "BirdNET"

# Storage of the daily detections
STORAGE_KEY: Final = f"{DOMAIN}.detections"
STORAGE_VERSION: Final = 1

# Frontend
URL_BASE: Final = "/birdnet_frontend"
CARD_FILENAME: Final = "birdnet-card.js"

# JS modules shipped with the integration and published to the Lovelace
# resources. The registered URL is bare: version tracking goes through the
# birdnet/version websocket command, not a ?v= parameter.
JSMODULES: Final[list[dict[str, str]]] = [
    {"name": "BirdNET Card", "filename": CARD_FILENAME},
]
