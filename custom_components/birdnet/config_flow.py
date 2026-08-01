"""Config flow de l'intégration BirdNET."""

from __future__ import annotations

from typing import Any

from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.core import callback
from homeassistant.helpers import selector
import voluptuous as vol

from .const import (
    CONF_EXCLUDED_SPECIES,
    CONF_MAX_DETECTIONS,
    CONF_MIN_CONFIDENCE,
    CONF_TOPIC,
    DEFAULT_MAX_DETECTIONS,
    DEFAULT_MIN_CONFIDENCE,
    DEFAULT_NAME,
    DEFAULT_TOPIC,
    DOMAIN,
)

_CONFIDENCE_SELECTOR = selector.NumberSelector(
    selector.NumberSelectorConfig(
        min=0, max=100, step=1, unit_of_measurement="%", mode=selector.NumberSelectorMode.SLIDER
    )
)
_SPECIES_SELECTOR = selector.SelectSelector(
    selector.SelectSelectorConfig(options=[], multiple=True, custom_value=True)
)


def _validate_topic(topic: str) -> str | None:
    """Retourne un code d'erreur si le topic MQTT est invalide."""
    topic = topic.strip()
    if not topic or topic.startswith("$"):
        return "invalid_topic"
    if any(char in topic for char in ("\0", " ")):
        return "invalid_topic"
    return None


class BirdNetConfigFlow(ConfigFlow, domain=DOMAIN):
    """Assistant de configuration."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Première (et unique) étape."""
        errors: dict[str, str] = {}

        if user_input is not None:
            topic = user_input[CONF_TOPIC].strip()
            if error := _validate_topic(topic):
                errors[CONF_TOPIC] = error
            else:
                await self.async_set_unique_id(topic)
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=DEFAULT_NAME,
                    data={CONF_TOPIC: topic},
                    options={
                        CONF_TOPIC: topic,
                        CONF_MIN_CONFIDENCE: user_input[CONF_MIN_CONFIDENCE],
                        CONF_EXCLUDED_SPECIES: user_input.get(
                            CONF_EXCLUDED_SPECIES, []
                        ),
                        CONF_MAX_DETECTIONS: DEFAULT_MAX_DETECTIONS,
                    },
                )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_TOPIC,
                        default=(user_input or {}).get(CONF_TOPIC, DEFAULT_TOPIC),
                    ): str,
                    vol.Required(
                        CONF_MIN_CONFIDENCE, default=DEFAULT_MIN_CONFIDENCE
                    ): _CONFIDENCE_SELECTOR,
                    vol.Optional(
                        CONF_EXCLUDED_SPECIES, default=[]
                    ): _SPECIES_SELECTOR,
                }
            ),
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        """Retourne le flux d'options."""
        return BirdNetOptionsFlow()


class BirdNetOptionsFlow(OptionsFlow):
    """Modification des options après installation."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Formulaire d'options."""
        errors: dict[str, str] = {}
        options = self.config_entry.options

        if user_input is not None:
            topic = user_input[CONF_TOPIC].strip()
            if error := _validate_topic(topic):
                errors[CONF_TOPIC] = error
            else:
                return self.async_create_entry(
                    data={**user_input, CONF_TOPIC: topic}
                )

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_TOPIC,
                        default=options.get(CONF_TOPIC, DEFAULT_TOPIC),
                    ): str,
                    vol.Required(
                        CONF_MIN_CONFIDENCE,
                        default=options.get(
                            CONF_MIN_CONFIDENCE, DEFAULT_MIN_CONFIDENCE
                        ),
                    ): _CONFIDENCE_SELECTOR,
                    vol.Optional(
                        CONF_EXCLUDED_SPECIES,
                        default=list(options.get(CONF_EXCLUDED_SPECIES, [])),
                    ): _SPECIES_SELECTOR,
                    vol.Required(
                        CONF_MAX_DETECTIONS,
                        default=options.get(
                            CONF_MAX_DETECTIONS, DEFAULT_MAX_DETECTIONS
                        ),
                    ): selector.NumberSelector(
                        selector.NumberSelectorConfig(
                            min=20, max=2000, step=10, mode=selector.NumberSelectorMode.BOX
                        )
                    ),
                }
            ),
            errors=errors,
        )
