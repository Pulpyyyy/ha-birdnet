/*!
 * BirdNET Card — carte Lovelace pour l'intégration BirdNET (MQTT).
 * Fonctionne avec sensor.birdnet_derniere_detection (intégration) ou avec un
 * template sensor exposant common_name / image / bird_events (tuto HACF).
 */

const CARD_VERSION = "1.0.0";

console.info(`%c 🙂 BirdNET Card %c v${CARD_VERSION} %c`, "background:#2196F3;color:white;padding:2px 8px;border-radius:3px 0 0 3px;font-weight:bold", "background:#4CAF50;color:white;padding:2px 8px;border-radius:0 3px 3px 0", "background:none");

const STRINGS = {
  fr: {
    noDetection: "Aucune détection",
    waiting: "En attente d'une détection…",
    today: "Aujourd'hui",
    species: (n) => `${n} espèce${n > 1 ? "s" : ""}`,
    detections: (n) => `${n} détection${n > 1 ? "s" : ""}`,
    entityMissing: "Entité introuvable",
    listen: "Écouter l'enregistrement",
    pause: "Pause",
    reload: "Recharger",
    versionMismatch: (backend, card) =>
      `BirdNET : la carte chargée (${card}) ne correspond pas à l'intégration ` +
      `(${backend}). Rechargez pour vider le cache.`,
    times: (n) => `${n} détection${n > 1 ? "s" : ""} aujourd'hui`,
    confidence: "fiabilité",
  },
  en: {
    noDetection: "No detection",
    waiting: "Waiting for a detection…",
    today: "Today",
    species: (n) => `${n} species`,
    detections: (n) => `${n} detection${n > 1 ? "s" : ""}`,
    entityMissing: "Entity not found",
    listen: "Play recording",
    pause: "Pause",
    reload: "Reload",
    versionMismatch: (backend, card) =>
      `BirdNET: the loaded card (${card}) does not match the integration ` +
      `(${backend}). Reload to clear the cache.`,
    times: (n) => `${n} detection${n > 1 ? "s" : ""} today`,
    confidence: "confidence",
  },
};

const DEFAULTS = {
  title: "",
  layout: "hero", // hero | compact
  show_image: true,
  show_chips: true, // nom scientifique + pastille de confiance
  show_log: true,
  show_audio: true,
  show_footer: true,
  log_min_confidence: 70,
  max_rows: 10,
  aspect_ratio: "16:9",
  emphasis: "confidence", // confidence | count
  wikipedia: true,
  wikipedia_language: "",
  tap_action: "url",
};

const esc = (value) =>
  String(value ?? "")
    .split("&").join("&amp;")
    .split("<").join("&lt;")
    .split(">").join("&gt;")
    .split('"').join("&quot;");

/** URL sûre : uniquement http(s) et chemins internes. */
const safeUrl = (value) => {
  if (typeof value !== "string") return "";
  const url = value.trim();
  const lower = url.toLowerCase();
  if (lower.startsWith("http://") || lower.startsWith("https://")) return url;
  if (url.startsWith("/")) return url;
  return "";
};

/** Confiance normalisée en pourcentage (accepte 0.98, 98, "98%"). */
const toPercent = (value) => {
  if (value === null || value === undefined || value === "") return null;
  const number = parseFloat(String(value).split("%").join("").split(",").join("."));
  if (Number.isNaN(number)) return null;
  return number <= 1 ? Math.round(number * 100) : Math.round(number);
};

/** Niveau qualitatif, sert au code couleur (pas d'alarme : une échelle). */
const confidenceLevel = (percent) => {
  if (percent === null) return "none";
  if (percent >= 90) return "high";
  if (percent >= 75) return "mid";
  return "low";
};

const parseRatio = (value) => {
  const parts = String(value || "16:9").split(":").join("/").split("/");
  const width = parseFloat(parts[0]);
  const height = parseFloat(parts[1]);
  if (!width || !height) return "16 / 9";
  return `${width} / ${height}`;
};

class BirdNetCard extends HTMLElement {
  static getConfigElement() {
    return document.createElement("birdnet-card-editor");
  }

  static getStubConfig(hass) {
    const ids = Object.keys(hass.states).filter(
      (id) => id.startsWith("sensor.") && id.includes("birdnet")
    );
    const entity =
      ids.find((id) => id.includes("last") || id.includes("derniere")) ||
      ids[0] ||
      "";
    return { entity };
  }

  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._signature = null;
    this._audio = null;
    this._playingUrl = null;
    this._versionChecked = false;
  }

  setConfig(config) {
    if (!config || !config.entity) {
      throw new Error("Renseignez une entité (entity).");
    }
    this._config = { ...DEFAULTS, ...config };
    this._signature = null;
    if (this._hass) this._render();
  }

  set hass(hass) {
    this._hass = hass;
    this._checkVersion();
    if (this._config) this._render();
  }

  disconnectedCallback() {
    this._stopAudio();
  }

  /**
   * Une URL versionnée ne suffit pas : une page déjà en cache (typiquement
   * l'application mobile) continue de charger l'ancien module. On compare donc
   * la version de la carte à celle que l'intégration annonce.
   */
  async _checkVersion() {
    if (this._versionChecked || !this._hass?.connection) return;
    this._versionChecked = true;
    try {
      const result = await this._hass.connection.sendMessagePromise({
        type: "birdnet/version",
      });
      if (result?.version && result.version !== CARD_VERSION) {
        this._notifyVersionMismatch(result.version);
      }
    } catch (err) {
      // Intégration absente : la carte sait aussi lire un template sensor,
      // il n'y a alors aucune version à comparer.
    }
  }

  _notifyVersionMismatch(backendVersion) {
    const t = this._t;
    console.warn(
      `[birdnet-card] version ${CARD_VERSION}, intégration ${backendVersion}`
    );
    this.dispatchEvent(
      new CustomEvent("hass-notification", {
        detail: {
          message: t.versionMismatch(backendVersion, CARD_VERSION),
          duration: -1,
          dismissable: true,
          action: { text: t.reload, action: () => this._reloadWithoutCache() },
        },
        bubbles: true,
        composed: true,
      })
    );
  }

  _reloadWithoutCache() {
    // L'API caches demande HTTPS ou localhost : repli sur un rechargement sec.
    if (!("caches" in window)) {
      window.location.reload();
      return;
    }
    caches
      .keys()
      .then((names) => Promise.all(names.map((name) => caches.delete(name))))
      .catch(() => undefined)
      .then(() => window.location.reload());
  }

  getCardSize() {
    const config = this._config || DEFAULTS;
    const media = config.show_image
      ? config.layout === "compact"
        ? 1
        : 3
      : 1;
    const rows = config.show_log ? Math.ceil((Number(config.max_rows) || 10) / 2) : 0;
    return media + 1 + rows;
  }

  // ---------------------------------------------------------------- données

  get _t() {
    const language = (this._hass?.locale?.language || "en").slice(0, 2);
    return STRINGS[language] || STRINGS.en;
  }

  /** Agrège le journal du jour, quelle que soit la forme de l'attribut. */
  _buildRows(attributes) {
    const summary = attributes.species;
    if (Array.isArray(summary) && summary.length && summary[0].name) {
      return summary.map((item) => ({
        name: item.name,
        scientific: item.scientific_name || "",
        time: String(item.last_time || "").slice(0, 5),
        count: item.count || 1,
        confidence: toPercent(item.max_confidence),
        link: safeUrl(item.link),
      }));
    }

    const events = Array.isArray(attributes.detections)
      ? attributes.detections
      : Array.isArray(attributes.bird_events)
        ? attributes.bird_events
        : [];

    const grouped = new Map();
    events.forEach((event) => {
      const name = event.name || event.common_name;
      if (!name) return;
      const key = name.toLowerCase();
      const time = String(event.time || "").slice(0, 5);
      const confidence = toPercent(event.confidence ?? event.confidence_score);
      const current = grouped.get(key);
      if (!current) {
        grouped.set(key, {
          name,
          scientific: event.scientific_name || "",
          time,
          count: 1,
          confidence,
          link: safeUrl(event.link),
        });
        return;
      }
      current.count += 1;
      if (
        confidence !== null &&
        (current.confidence === null || confidence > current.confidence)
      ) {
        current.confidence = confidence;
      }
      if (time > current.time) {
        current.time = time;
        current.link = safeUrl(event.link) || current.link;
      }
    });
    return [...grouped.values()].sort((a, b) => b.time.localeCompare(a.time));
  }

  _speciesUrl(name, force = false) {
    if ((!this._config.wikipedia && !force) || !name) return "";
    const language =
      this._config.wikipedia_language ||
      (this._hass?.locale?.language || "en").slice(0, 2);
    return `https://${language}.wikipedia.org/wiki/${encodeURIComponent(
      String(name).split(" ").join("_")
    )}`;
  }

  // ---------------------------------------------------------------- rendu

  _render() {
    const config = this._config;
    const stateObj = this._hass.states[config.entity];

    if (!stateObj) {
      const signature = `missing:${config.entity}`;
      if (signature === this._signature) return;
      this._signature = signature;
      this._paint(`
        <div class="notice notice--error">
          <ha-icon icon="mdi:alert-circle-outline"></ha-icon>
          <span>${esc(this._t.entityMissing)} : ${esc(config.entity)}</span>
        </div>`);
      return;
    }

    const t = this._t;
    const attributes = stateObj.attributes || {};
    const unavailable = ["unknown", "unavailable"].includes(stateObj.state);
    const name = attributes.common_name || (unavailable ? "" : stateObj.state) || "";
    const scientific = attributes.scientific_name || "";
    const confidence = toPercent(attributes.confidence ?? attributes.confidence_score);
    const time = String(attributes.time || "").slice(0, 5);
    const image = config.show_image
      ? safeUrl(attributes.image || attributes.entity_picture)
      : "";
    const link = safeUrl(attributes.link);
    const audio = config.show_audio ? safeUrl(attributes.audio) : "";

    const rows = this._buildRows(attributes);
    const threshold = Number(config.log_min_confidence) || 0;
    const visibleRows = rows
      .filter((row) => row.confidence === null || row.confidence >= threshold)
      .slice(0, Number(config.max_rows) || 10);

    const speciesCount = attributes.species_count ?? rows.length;
    const detectionCount =
      attributes.detection_count ?? rows.reduce((total, row) => total + row.count, 0);

    const signature = JSON.stringify([
      name,
      time,
      image,
      confidence,
      audio,
      visibleRows,
      speciesCount,
      detectionCount,
      config,
    ]);
    if (signature === this._signature) return;
    this._signature = signature;

    const parts = [];
    if (config.title) {
      parts.push(`<div class="title">${esc(config.title)}</div>`);
    }
    parts.push(
      this._renderHeader({ name, scientific, confidence, time, image, audio, t })
    );
    if (config.show_log) {
      parts.push(
        this._renderLog({ visibleRows, speciesCount, detectionCount, t })
      );
    }

    const target =
      config.tap_action === "wikipedia"
        ? this._speciesUrl(name, true)
        : link || this._speciesUrl(name);

    this._paint(parts.join(""), image ? parseRatio(config.aspect_ratio) : null);
    this._bindActions(target, audio);
  }

  _renderHeader({ name, scientific, confidence, time, image, audio, t }) {
    const config = this._config;
    const level = confidenceLevel(confidence);
    const label = esc(name || t.noDetection);
    const meta = [];
    if (config.show_chips && scientific) {
      meta.push(`<em class="latin">${esc(scientific)}</em>`);
    }
    meta.push(
      time
        ? `<span class="time"><ha-icon icon="mdi:clock-outline"></ha-icon>${esc(time)}</span>`
        : `<span class="time">${esc(t.waiting)}</span>`
    );
    const metaHtml = meta.join('<span class="sep"></span>');

    const pill =
      config.show_chips && confidence !== null
        ? `<span class="pill pill--${level}" title="${confidence} % ${esc(t.confidence)}">
             <ha-icon icon="mdi:shield-check"></ha-icon>${confidence}%
           </span>`
        : "";

    const playing = audio && this._playingUrl === audio;
    const playButton = audio
      ? `<button class="play" data-audio="${esc(audio)}"
                 aria-label="${esc(playing ? t.pause : t.listen)}"
                 title="${esc(playing ? t.pause : t.listen)}">
           <ha-icon icon="${playing ? "mdi:pause" : "mdi:play"}"></ha-icon>
         </button>`
      : "";

    // Grande image : titre en incrustation sur un dégradé, zéro ligne perdue.
    if (image && config.layout !== "compact") {
      return `
        <div class="hero" data-action="primary" role="button" tabindex="0">
          <img class="hero__img" src="${esc(image)}" alt="${label}" loading="lazy" />
          <div class="hero__scrim"></div>
          <div class="hero__top">${pill}${playButton}</div>
          <div class="hero__body">
            <div class="hero__name">${label}</div>
            <div class="hero__meta">${metaHtml}</div>
          </div>
        </div>`;
    }

    // Vignette ou pastille d'icône : une seule bande de 64 px.
    const thumb = image
      ? `<img class="thumb" src="${esc(image)}" alt="${label}" loading="lazy" />`
      : `<div class="thumb thumb--icon"><ha-icon icon="mdi:bird"></ha-icon></div>`;

    return `
      <div class="strip" data-action="primary" role="button" tabindex="0">
        ${thumb}
        <div class="strip__body">
          <div class="strip__name">${label}</div>
          <div class="strip__meta">${metaHtml}</div>
        </div>
        <div class="strip__aside">${pill}${playButton}</div>
      </div>`;
  }

  _renderLog({ visibleRows, speciesCount, detectionCount, t }) {
    const config = this._config;
    const stats = config.show_footer
      ? `<span class="log__stats">${esc(t.species(speciesCount))}
           <span class="sep"></span>${esc(t.detections(detectionCount))}</span>`
      : "";
    const head = `
      <div class="log__head">
        <span class="log__title">${esc(t.today)}</span>
        ${stats}
      </div>`;

    if (!visibleRows.length) {
      return `<div class="log">${head}
        <div class="notice"><ha-icon icon="mdi:sleep"></ha-icon>
          <span>${esc(t.noDetection)}</span></div>
      </div>`;
    }

    // La colonne mise en avant (valeur en gras à droite + jauge) suit l'option
    // emphasis ; l'autre information reste lisible, en retrait.
    const byCount = config.emphasis === "count";
    const maxCount = Math.max(...visibleRows.map((row) => row.count), 1);
    const ordered = byCount
      ? [...visibleRows].sort(
          (a, b) => b.count - a.count || b.time.localeCompare(a.time)
        )
      : visibleRows;

    const rows = ordered
      .map((row) => {
        const url = row.link || this._speciesUrl(row.name);
        const confidenceText = row.confidence === null ? "—" : `${row.confidence}%`;
        const ratio = row.count / maxCount;

        const level = byCount
          ? ratio >= 0.66
            ? "high"
            : ratio >= 0.33
              ? "mid"
              : "low"
          : confidenceLevel(row.confidence);
        const major = byCount ? `×${row.count}` : confidenceText;
        const minor = byCount ? confidenceText : `×${row.count}`;
        const width = byCount ? Math.round(ratio * 100) : row.confidence;

        const nameHtml = url
          ? `<a class="row__name" href="${esc(url)}" target="_blank" rel="noopener noreferrer">${esc(row.name)}</a>`
          : `<span class="row__name">${esc(row.name)}</span>`;
        const minorClass =
          !byCount && row.count === 1 ? "row__minor row__minor--faded" : "row__minor";
        const gauge =
          width === null
            ? ""
            : `<span class="gauge gauge--${level}"><i style="width:${width}%"></i></span>`;

        return `
          <li class="row">
            <span class="row__time">${esc(row.time || "—")}</span>
            ${nameHtml}
            <span class="${minorClass}">${esc(minor)}</span>
            <span class="row__major conf--${level}" title="${esc(t.times(row.count))}">${esc(major)}</span>
            ${gauge}
          </li>`;
      })
      .join("");

    return `<div class="log">${head}<ol class="rows">${rows}</ol></div>`;
  }

  _paint(inner, ratio) {
    const style = ratio ? ` style="--birdnet-ratio: ${ratio}"` : "";
    this.shadowRoot.innerHTML = `<style>${BirdNetCard.styles}</style>
      <ha-card${style}>${inner}</ha-card>`;

    // Une image cassée (Flickr expiré, hôte injoignable) ne doit pas laisser
    // un trou : on bascule sur la mise en page sans média.
    const img = this.shadowRoot.querySelector("img");
    if (img) {
      img.addEventListener("error", () => {
        this._signature = null;
        const card = this.shadowRoot.querySelector("ha-card");
        if (card) card.classList.add("no-media");
        img.remove();
      });
    }
  }

  // ---------------------------------------------------------------- actions

  _bindActions(target, audio) {
    const action = this._config.tap_action;

    if (action !== "none") {
      const handler = () => {
        if (action === "more-info") {
          this.dispatchEvent(
            new CustomEvent("hass-more-info", {
              detail: { entityId: this._config.entity },
              bubbles: true,
              composed: true,
            })
          );
        } else if (target) {
          window.open(target, "_blank", "noopener");
        }
      };
      this.shadowRoot.querySelectorAll('[data-action="primary"]').forEach((node) => {
        node.addEventListener("click", handler);
        node.addEventListener("keydown", (event) => {
          if (event.key === "Enter" || event.key === " ") {
            event.preventDefault();
            handler();
          }
        });
      });
    }

    const play = this.shadowRoot.querySelector(".play");
    if (play && audio) {
      play.addEventListener("click", (event) => {
        event.stopPropagation();
        this._toggleAudio(audio);
      });
    }
  }

  _toggleAudio(url) {
    if (this._playingUrl === url) {
      this._stopAudio();
      return;
    }
    this._stopAudio();
    const audio = new Audio(url);
    audio.addEventListener("ended", () => this._stopAudio());
    audio.addEventListener("error", () => this._stopAudio());
    audio.play().catch(() => this._stopAudio());
    this._audio = audio;
    this._playingUrl = url;
    this._refreshPlayButton();
  }

  _stopAudio() {
    if (this._audio) {
      this._audio.pause();
      this._audio = null;
    }
    this._playingUrl = null;
    this._refreshPlayButton();
  }

  _refreshPlayButton() {
    const button = this.shadowRoot?.querySelector(".play");
    if (!button) return;
    const playing = this._playingUrl === button.dataset.audio;
    const label = playing ? this._t.pause : this._t.listen;
    button.classList.toggle("play--active", playing);
    button.setAttribute("aria-label", label);
    button.setAttribute("title", label);
    const icon = button.querySelector("ha-icon");
    if (icon) icon.setAttribute("icon", playing ? "mdi:pause" : "mdi:play");
  }

  // ---------------------------------------------------------------- styles

  static get styles() {
    return `
      :host {
        --birdnet-gap: 16px;
        --birdnet-radius: 12px;
        /* Échelle de fiabilité sur une seule teinte, celle du thème : primaire
           franche, primaire atténuée, puis gris. */
        --birdnet-high: var(--primary-color, #03a9f4);
        --birdnet-mid: color-mix(
          in srgb,
          var(--primary-color, #03a9f4) 55%,
          var(--secondary-text-color, #727272)
        );
        --birdnet-low: var(--secondary-text-color, #727272);
      }
      ha-card {
        overflow: hidden;
        display: flex;
        flex-direction: column;
        /* La carte se mesure elle-même : elle s'adapte à sa colonne, pas à
           la largeur de l'écran. */
        container-type: inline-size;
        container-name: birdnet;
      }
      .title {
        font-size: 16px;
        font-weight: 600;
        letter-spacing: 0.01em;
        color: var(--ha-card-header-color, var(--primary-text-color));
        padding: 14px var(--birdnet-gap) 0;
      }

      /* ---------------------------------------------------- média + espèce */
      .hero {
        position: relative;
        cursor: pointer;
        line-height: 0;
        isolation: isolate;
      }
      .hero:focus-visible { outline: 2px solid var(--primary-color); outline-offset: -2px; }
      .hero__img {
        width: 100%;
        aspect-ratio: var(--birdnet-ratio, 16 / 9);
        object-fit: cover;
        display: block;
      }
      .hero__scrim {
        position: absolute;
        inset: 0;
        background: linear-gradient(
          to top,
          rgba(0, 0, 0, 0.78) 0%,
          rgba(0, 0, 0, 0.42) 28%,
          rgba(0, 0, 0, 0) 58%
        );
      }
      .hero__top {
        position: absolute;
        top: 10px;
        right: 10px;
        display: flex;
        align-items: center;
        gap: 8px;
        line-height: 1;
      }
      .hero__body {
        position: absolute;
        left: var(--birdnet-gap);
        right: var(--birdnet-gap);
        bottom: 12px;
        line-height: 1.25;
      }
      .hero__name {
        color: #fff;
        font-size: 20px;
        font-weight: 600;
        letter-spacing: -0.01em;
        text-shadow: 0 1px 3px rgba(0, 0, 0, 0.45);
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
      }
      .hero__meta {
        display: flex;
        align-items: center;
        gap: 8px;
        margin-top: 2px;
        font-size: 13px;
        color: rgba(255, 255, 255, 0.85);
        text-shadow: 0 1px 3px rgba(0, 0, 0, 0.45);
      }
      .hero .sep { background: rgba(255, 255, 255, 0.55); }
      .hero__meta ha-icon { --mdc-icon-size: 15px; margin-right: 3px; }

      .strip {
        display: flex;
        align-items: center;
        gap: 12px;
        padding: 12px var(--birdnet-gap);
        cursor: pointer;
      }
      .strip:focus-visible { outline: 2px solid var(--primary-color); outline-offset: -2px; }
      .thumb {
        flex: 0 0 auto;
        width: 56px;
        height: 56px;
        border-radius: var(--birdnet-radius);
        object-fit: cover;
        display: block;
      }
      .thumb--icon {
        display: flex;
        align-items: center;
        justify-content: center;
        background: rgba(var(--rgb-primary-color, 3, 169, 244), 0.14);
        color: var(--primary-color);
      }
      .thumb--icon ha-icon { --mdc-icon-size: 28px; }
      .strip__body { min-width: 0; flex: 1 1 auto; }
      .strip__name {
        font-size: 16px;
        font-weight: 600;
        color: var(--primary-text-color);
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
      }
      .strip__meta {
        display: flex;
        align-items: center;
        gap: 8px;
        margin-top: 2px;
        font-size: 13px;
        color: var(--secondary-text-color);
      }
      .strip__meta ha-icon { --mdc-icon-size: 15px; margin-right: 3px; }
      .strip__aside {
        flex: 0 0 auto;
        display: flex;
        align-items: center;
        gap: 8px;
      }
      .latin {
        font-style: italic;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
      }
      .time { display: inline-flex; align-items: center; white-space: nowrap; }
      .sep {
        width: 3px;
        height: 3px;
        border-radius: 50%;
        background: currentColor;
        opacity: 0.5;
        flex: 0 0 auto;
      }

      /* --------------------------------------------------------- pastilles */
      .pill {
        display: inline-flex;
        align-items: center;
        gap: 4px;
        height: 26px;
        padding: 0 9px;
        border-radius: 13px;
        font-size: 12px;
        font-weight: 600;
        font-variant-numeric: tabular-nums;
        color: #fff;
        background: var(--birdnet-low);
        backdrop-filter: blur(2px);
      }
      .pill ha-icon { --mdc-icon-size: 14px; }
      .pill--high { background: var(--birdnet-high); }
      .pill--mid { background: var(--birdnet-mid); }
      .pill--low { background: rgba(0, 0, 0, 0.55); }
      .strip .pill--low { background: var(--birdnet-low); }

      .play {
        width: 30px;
        height: 30px;
        border: none;
        border-radius: 50%;
        padding: 0;
        cursor: pointer;
        display: inline-flex;
        align-items: center;
        justify-content: center;
        color: var(--primary-text-color);
        background: var(--card-background-color, #fff);
        box-shadow: 0 1px 4px rgba(0, 0, 0, 0.28);
        transition: transform 120ms ease;
      }
      .play:hover { transform: scale(1.08); }
      .play:focus-visible { outline: 2px solid var(--primary-color); outline-offset: 2px; }
      .play ha-icon { --mdc-icon-size: 18px; }
      .play--active { color: var(--primary-color); }

      /* ----------------------------------------------------------- journal */
      .log {
        border-top: 1px solid var(--divider-color);
        padding: 10px var(--birdnet-gap) 12px;
      }
      ha-card.no-media .log { border-top: none; }
      .log__head {
        display: flex;
        align-items: baseline;
        justify-content: space-between;
        gap: 12px;
        margin-bottom: 4px;
      }
      .log__title {
        font-size: 11px;
        font-weight: 700;
        letter-spacing: 0.08em;
        text-transform: uppercase;
        color: var(--secondary-text-color);
      }
      .log__stats {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        font-size: 12px;
        font-variant-numeric: tabular-nums;
        color: var(--secondary-text-color);
        white-space: nowrap;
      }
      .rows { list-style: none; margin: 0; padding: 0; }
      .row {
        display: grid;
        grid-template-columns: auto 1fr auto auto;
        align-items: center;
        column-gap: 10px;
        row-gap: 3px;
        padding: 5px 0;
        border-bottom: 1px solid var(--divider-color);
      }
      .row:last-child { border-bottom: none; }
      .row__time {
        font-size: 12px;
        font-variant-numeric: tabular-nums;
        color: var(--secondary-text-color);
        white-space: nowrap;
      }
      .row__name {
        font-size: 14px;
        color: var(--primary-text-color);
        text-decoration: none;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
      }
      a.row__name:hover { text-decoration: underline; }
      .row__minor {
        font-size: 12px;
        font-variant-numeric: tabular-nums;
        color: var(--secondary-text-color);
        white-space: nowrap;
      }
      .row__minor--faded { opacity: 0.45; }
      .row__major {
        font-size: 13px;
        font-weight: 600;
        font-variant-numeric: tabular-nums;
        white-space: nowrap;
        min-width: 38px;
        text-align: right;
      }
      .conf--high { color: var(--birdnet-high); }
      .conf--mid { color: var(--birdnet-mid); }
      .conf--low, .conf--none { color: var(--secondary-text-color); }
      .gauge {
        grid-column: 2 / -1;
        height: 3px;
        border-radius: 2px;
        background: var(--divider-color);
        overflow: hidden;
      }
      .gauge i {
        display: block;
        height: 100%;
        border-radius: 2px;
        background: var(--birdnet-low);
      }
      .gauge--high i { background: var(--birdnet-high); }
      .gauge--mid i { background: var(--birdnet-mid); }

      .notice {
        display: flex;
        align-items: center;
        gap: 8px;
        padding: 10px 0 4px;
        font-size: 13px;
        color: var(--secondary-text-color);
      }
      .notice ha-icon { --mdc-icon-size: 18px; }
      .notice--error { color: var(--error-color, #db4437); padding: 14px var(--birdnet-gap); }

      /* ------------------------------------------------------ responsive */
      /* Colonne étroite (mobile, sidebar) : on resserre et on laisse la
         ligne secondaire passer à la ligne plutôt que de tronquer. */
      @container birdnet (max-width: 330px) {
        :host { --birdnet-gap: 12px; }
        .hero__name { font-size: 17px; }
        .hero__meta, .strip__meta { flex-wrap: wrap; row-gap: 0; font-size: 12px; }
        .thumb { width: 48px; height: 48px; }
        .strip__name { font-size: 15px; }
        .row { column-gap: 8px; }
        .row__time { font-size: 11px; }
        .row__name { font-size: 13px; }
        .log__stats { font-size: 11px; }
      }
      /* Vraiment étroit : les totaux passent sous le titre du journal, rien
         n'est masqué pour autant. */
      @container birdnet (max-width: 260px) {
        .log__head { flex-direction: column; align-items: flex-start; gap: 2px; }
        .log__stats { white-space: normal; }
        .row__major { min-width: 0; }
      }
      /* Carte large : on gagne de la hauteur en passant le journal sur deux
         colonnes, et l'entête respire. */
      @container birdnet (min-width: 520px) {
        :host { --birdnet-gap: 20px; }
        .hero__name { font-size: 24px; }
        .hero__meta, .strip__meta { font-size: 14px; }
        .rows {
          display: grid;
          grid-template-columns: 1fr 1fr;
          column-gap: 28px;
        }
        .rows .row:nth-last-child(2):nth-child(odd) { border-bottom: none; }
      }
      @container birdnet (min-width: 760px) {
        .rows { grid-template-columns: repeat(3, 1fr); }
      }

      @media (prefers-reduced-motion: reduce) {
        .play { transition: none; }
        .play:hover { transform: none; }
      }
    `;
  }
}

// ---------------------------------------------------------------- éditeur

const EDITOR_SCHEMA = [
  { name: "entity", required: true, selector: { entity: { domain: "sensor" } } },
  {
    type: "grid",
    schema: [
      { name: "title", selector: { text: {} } },
      {
        name: "layout",
        selector: {
          select: {
            mode: "dropdown",
            options: [
              { value: "hero", label: "Grande photo" },
              { value: "compact", label: "Vignette compacte" },
            ],
          },
        },
      },
    ],
  },
  {
    type: "grid",
    schema: [
      { name: "show_image", selector: { boolean: {} } },
      { name: "show_chips", selector: { boolean: {} } },
      { name: "show_log", selector: { boolean: {} } },
      { name: "show_audio", selector: { boolean: {} } },
      { name: "show_footer", selector: { boolean: {} } },
      { name: "wikipedia", selector: { boolean: {} } },
    ],
  },
  {
    type: "grid",
    schema: [
      {
        name: "max_rows",
        selector: { number: { min: 1, max: 50, step: 1, mode: "box" } },
      },
      {
        name: "log_min_confidence",
        selector: { number: { min: 0, max: 100, step: 5, mode: "slider" } },
      },
      { name: "aspect_ratio", selector: { text: {} } },
      { name: "wikipedia_language", selector: { text: {} } },
    ],
  },
  {
    name: "emphasis",
    selector: {
      select: {
        mode: "dropdown",
        options: [
          { value: "confidence", label: "La fiabilité (%)" },
          { value: "count", label: "Le nombre de détections" },
        ],
      },
    },
  },
  {
    name: "tap_action",
    selector: {
      select: {
        mode: "dropdown",
        options: [
          { value: "url", label: "Ouvrir le lien BirdNET" },
          { value: "wikipedia", label: "Ouvrir la fiche Wikipédia" },
          { value: "more-info", label: "Fiche de l'entité" },
          { value: "none", label: "Aucune" },
        ],
      },
    },
  },
];

const EDITOR_LABELS = {
  entity: "Entité BirdNET",
  title: "Titre (optionnel)",
  layout: "Mise en page",
  show_image: "Photo",
  show_chips: "Nom latin + fiabilité",
  show_log: "Journal du jour",
  show_audio: "Lecture de l'enregistrement",
  show_footer: "Totaux du jour",
  wikipedia: "Liens Wikipédia",
  wikipedia_language: "Langue Wikipédia",
  max_rows: "Lignes affichées",
  log_min_confidence: "Seuil du journal (%)",
  aspect_ratio: "Format de la photo",
  emphasis: "Mettre en valeur dans le journal",
  tap_action: "Action au clic",
};

class BirdNetCardEditor extends HTMLElement {
  setConfig(config) {
    this._config = { ...DEFAULTS, ...config };
    this._update();
  }

  set hass(hass) {
    this._hass = hass;
    this._update();
  }

  connectedCallback() {
    this._update();
  }

  _update() {
    if (!this._config || !this._hass) return;
    if (!this._form) {
      this._form = document.createElement("ha-form");
      this._form.computeLabel = (schema) => EDITOR_LABELS[schema.name] || schema.name;
      this._form.addEventListener("value-changed", (event) => {
        event.stopPropagation();
        this.dispatchEvent(
          new CustomEvent("config-changed", {
            detail: { config: event.detail.value },
            bubbles: true,
            composed: true,
          })
        );
      });
      this.appendChild(this._form);
    }
    this._form.hass = this._hass;
    this._form.schema = EDITOR_SCHEMA;
    this._form.data = this._config;
  }
}

customElements.define("birdnet-card", BirdNetCard);
customElements.define("birdnet-card-editor", BirdNetCardEditor);

window.customCards = window.customCards || [];
window.customCards.push({
  type: "birdnet-card",
  name: "BirdNET",
  description:
    "Dernière détection BirdNET (photo, espèce, fiabilité, écoute) et journal des espèces du jour.",
  preview: true,
  documentationURL: "https://github.com/Pulpyyyy/ha-birdnet",
});
