"""Constantes de l'intégration BirdNET."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Final

DOMAIN: Final = "birdnet"

# La version fait foi pour le cache-busting de la ressource Lovelace et pour la
# vérification de version côté carte.
MANIFEST_PATH: Final = Path(__file__).parent / "manifest.json"
with MANIFEST_PATH.open(encoding="utf-8") as manifest_file:
    INTEGRATION_VERSION: Final[str] = json.load(manifest_file).get("version", "0.0.0")

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

# Modules JS livrés avec l'intégration et publiés dans les ressources Lovelace.
JSMODULES: Final[list[dict[str, str]]] = [
    {
        "name": "BirdNET Card",
        "filename": CARD_FILENAME,
        "version": INTEGRATION_VERSION,
    },
]
