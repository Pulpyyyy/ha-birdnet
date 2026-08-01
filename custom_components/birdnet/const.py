"""Constantes de l'intégration BirdNET."""

from __future__ import annotations

from typing import Final

DOMAIN: Final = "birdnet"

# Configuration
CONF_TOPIC: Final = "topic"
CONF_MIN_CONFIDENCE: Final = "min_confidence"
CONF_EXCLUDED_SPECIES: Final = "excluded_species"
CONF_MAX_DETECTIONS: Final = "max_detections"
CONF_BASE_URL: Final = "base_url"

DEFAULT_TOPIC: Final = "birdnet/detection"
DEFAULT_MIN_CONFIDENCE: Final = 70
DEFAULT_MAX_DETECTIONS: Final = 500
DEFAULT_NAME: Final = "BirdNET"

# Stockage des détections du jour
STORAGE_KEY: Final = f"{DOMAIN}.detections"
STORAGE_VERSION: Final = 1

# Frontend
URL_BASE: Final = "/birdnet_frontend"
CARD_FILENAME: Final = "birdnet-card.js"
