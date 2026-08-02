/*!
 * BirdNET Card — Lovelace card for the BirdNET integration (MQTT).
 * Works with sensor.birdnet_last_detection (shipped by the integration) or with
 * any template sensor exposing common_name / image / bird_events.
 */

const CARD_VERSION = "1.0.1";

console.info(`%c 🙂 BirdNET Card %c v${CARD_VERSION} %c`, "background:#2196F3;color:white;padding:2px 8px;border-radius:3px 0 0 3px;font-weight:bold", "background:#4CAF50;color:white;padding:2px 8px;border-radius:0 3px 3px 0", "background:none");

const STRINGS = {
  en: {
    noDetection: "No detection",
    waiting: "Waiting for a detection…",
    today: "Today",
    species: (n) => `${n} species`,
    detections: (n) => `${n} detection${n > 1 ? "s" : ""}`,
    times: (n) => `${n} detection${n > 1 ? "s" : ""} today`,
    confidenceTitle: (p) => `${p}% confidence`,
    entityMissing: "Entity not found",
    listen: "Play recording",
    pause: "Pause",
    reload: "Reload",
    versionMismatch: (backend, card) =>
      `BirdNET: the loaded card (${card}) does not match the integration ` +
      `(${backend}). Reload to clear the cache.`,
    labels: {
      entity: "BirdNET entity",
      title: "Title (optional)",
      layout: "Layout",
      show_image: "Picture",
      show_chips: "Scientific name + confidence",
      show_log: "Today's log",
      show_audio: "Recording playback",
      show_footer: "Daily totals",
      wikipedia: "Wikipedia links",
      wikipedia_language: "Wikipedia language",
      max_rows: "Rows shown",
      log_min_confidence: "Log threshold (%)",
      aspect_ratio: "Picture aspect ratio",
      emphasis: "Highlight in the log",
      sort: "Log order",
      tap_action: "Tap action",
    },
    options: {
      hero: "Large picture",
      compact: "Compact thumbnail",
      minimal: "Single band, no log",
      confidence: "Confidence (%)",
      count: "Number of detections",
      sortAuto: "Follow the highlight",
      sortTime: "Most recent first",
      sortCount: "Most detections first",
      sortConfidence: "Highest confidence first",
      url: "Open the BirdNET link",
      wikipedia: "Open the Wikipedia page",
      moreInfo: "Entity details",
      none: "None",
    },
  },

  fr: {
    noDetection: "Aucune détection",
    waiting: "En attente d'une détection…",
    today: "Aujourd'hui",
    species: (n) => `${n} espèce${n > 1 ? "s" : ""}`,
    detections: (n) => `${n} détection${n > 1 ? "s" : ""}`,
    times: (n) => `${n} détection${n > 1 ? "s" : ""} aujourd'hui`,
    confidenceTitle: (p) => `${p} % de fiabilité`,
    entityMissing: "Entité introuvable",
    listen: "Écouter l'enregistrement",
    pause: "Pause",
    reload: "Recharger",
    versionMismatch: (backend, card) =>
      `BirdNET : la carte chargée (${card}) ne correspond pas à l'intégration ` +
      `(${backend}). Rechargez pour vider le cache.`,
    labels: {
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
      sort: "Tri du journal",
      tap_action: "Action au clic",
    },
    options: {
      hero: "Grande photo",
      compact: "Vignette compacte",
      minimal: "Bande unique, sans journal",
      confidence: "La fiabilité (%)",
      count: "Le nombre de détections",
      sortAuto: "Suivre la mise en valeur",
      sortTime: "Plus récent en premier",
      sortCount: "Plus de détections en premier",
      sortConfidence: "Meilleure fiabilité en premier",
      url: "Ouvrir le lien BirdNET",
      wikipedia: "Ouvrir la fiche Wikipédia",
      moreInfo: "Fiche de l'entité",
      none: "Aucune",
    },
  },

  de: {
    noDetection: "Keine Erkennung",
    waiting: "Warte auf eine Erkennung…",
    today: "Heute",
    species: (n) => `${n} Art${n > 1 ? "en" : ""}`,
    detections: (n) => `${n} Erkennung${n > 1 ? "en" : ""}`,
    times: (n) => `${n} Erkennung${n > 1 ? "en" : ""} heute`,
    confidenceTitle: (p) => `${p} % Zuverlässigkeit`,
    entityMissing: "Entität nicht gefunden",
    listen: "Aufnahme abspielen",
    pause: "Pause",
    reload: "Neu laden",
    versionMismatch: (backend, card) =>
      `BirdNET: Die geladene Karte (${card}) passt nicht zur Integration ` +
      `(${backend}). Zum Leeren des Caches neu laden.`,
    labels: {
      entity: "BirdNET-Entität",
      title: "Titel (optional)",
      layout: "Layout",
      show_image: "Bild",
      show_chips: "Wissenschaftlicher Name + Zuverlässigkeit",
      show_log: "Protokoll des Tages",
      show_audio: "Aufnahme abspielen",
      show_footer: "Tagessummen",
      wikipedia: "Wikipedia-Links",
      wikipedia_language: "Wikipedia-Sprache",
      max_rows: "Angezeigte Zeilen",
      log_min_confidence: "Schwelle für das Protokoll (%)",
      aspect_ratio: "Seitenverhältnis des Bildes",
      emphasis: "Im Protokoll hervorheben",
      sort: "Sortierung des Protokolls",
      tap_action: "Aktion beim Tippen",
    },
    options: {
      hero: "Großes Bild",
      compact: "Kompaktes Vorschaubild",
      minimal: "Einzelne Leiste, ohne Protokoll",
      confidence: "Zuverlässigkeit (%)",
      count: "Anzahl der Erkennungen",
      sortAuto: "Der Hervorhebung folgen",
      sortTime: "Neueste zuerst",
      sortCount: "Meiste Erkennungen zuerst",
      sortConfidence: "Höchste Zuverlässigkeit zuerst",
      url: "BirdNET-Link öffnen",
      wikipedia: "Wikipedia-Seite öffnen",
      moreInfo: "Entitätsdetails",
      none: "Keine",
    },
  },

  es: {
    noDetection: "Sin detección",
    waiting: "Esperando una detección…",
    today: "Hoy",
    species: (n) => `${n} especie${n > 1 ? "s" : ""}`,
    detections: (n) => `${n} ${n > 1 ? "detecciones" : "detección"}`,
    times: (n) => `${n} ${n > 1 ? "detecciones" : "detección"} hoy`,
    confidenceTitle: (p) => `${p} % de fiabilidad`,
    entityMissing: "Entidad no encontrada",
    listen: "Reproducir la grabación",
    pause: "Pausa",
    reload: "Recargar",
    versionMismatch: (backend, card) =>
      `BirdNET: la tarjeta cargada (${card}) no coincide con la integración ` +
      `(${backend}). Recarga para vaciar la caché.`,
    labels: {
      entity: "Entidad BirdNET",
      title: "Título (opcional)",
      layout: "Diseño",
      show_image: "Foto",
      show_chips: "Nombre científico + fiabilidad",
      show_log: "Registro del día",
      show_audio: "Reproducción de la grabación",
      show_footer: "Totales del día",
      wikipedia: "Enlaces de Wikipedia",
      wikipedia_language: "Idioma de Wikipedia",
      max_rows: "Filas mostradas",
      log_min_confidence: "Umbral del registro (%)",
      aspect_ratio: "Formato de la foto",
      emphasis: "Destacar en el registro",
      sort: "Orden del registro",
      tap_action: "Acción al pulsar",
    },
    options: {
      hero: "Foto grande",
      compact: "Miniatura compacta",
      minimal: "Banda única, sin registro",
      confidence: "La fiabilidad (%)",
      count: "El número de detecciones",
      sortAuto: "Seguir el elemento destacado",
      sortTime: "Más reciente primero",
      sortCount: "Más detecciones primero",
      sortConfidence: "Mayor fiabilidad primero",
      url: "Abrir el enlace de BirdNET",
      wikipedia: "Abrir la página de Wikipedia",
      moreInfo: "Detalles de la entidad",
      none: "Ninguna",
    },
  },

  it: {
    noDetection: "Nessun rilevamento",
    waiting: "In attesa di un rilevamento…",
    today: "Oggi",
    species: (n) => `${n} specie`,
    detections: (n) => `${n} rilevament${n > 1 ? "i" : "o"}`,
    times: (n) => `${n} rilevament${n > 1 ? "i" : "o"} oggi`,
    confidenceTitle: (p) => `${p} % di affidabilità`,
    entityMissing: "Entità non trovata",
    listen: "Riproduci la registrazione",
    pause: "Pausa",
    reload: "Ricarica",
    versionMismatch: (backend, card) =>
      `BirdNET: la scheda caricata (${card}) non corrisponde all'integrazione ` +
      `(${backend}). Ricarica per svuotare la cache.`,
    labels: {
      entity: "Entità BirdNET",
      title: "Titolo (opzionale)",
      layout: "Disposizione",
      show_image: "Foto",
      show_chips: "Nome scientifico + affidabilità",
      show_log: "Registro del giorno",
      show_audio: "Riproduzione della registrazione",
      show_footer: "Totali del giorno",
      wikipedia: "Collegamenti a Wikipedia",
      wikipedia_language: "Lingua di Wikipedia",
      max_rows: "Righe mostrate",
      log_min_confidence: "Soglia del registro (%)",
      aspect_ratio: "Formato della foto",
      emphasis: "Evidenzia nel registro",
      sort: "Ordine del registro",
      tap_action: "Azione al tocco",
    },
    options: {
      hero: "Foto grande",
      compact: "Miniatura compatta",
      minimal: "Banda singola, senza registro",
      confidence: "L'affidabilità (%)",
      count: "Il numero di rilevamenti",
      sortAuto: "Segui l'evidenziazione",
      sortTime: "Più recente prima",
      sortCount: "Più rilevamenti prima",
      sortConfidence: "Maggiore affidabilità prima",
      url: "Apri il collegamento BirdNET",
      wikipedia: "Apri la pagina di Wikipedia",
      moreInfo: "Dettagli dell'entità",
      none: "Nessuna",
    },
  },
};

/** Pick the translation table matching the user's Home Assistant language. */
const localize = (hass) => {
  const language = (hass?.locale?.language || "en").slice(0, 2);
  return STRINGS[language] || STRINGS.en;
};

const DEFAULTS = {
  title: "",
  layout: "hero", // hero | compact | minimal (compact without the log)
  show_image: true,
  show_chips: true, // scientific name + confidence pill
  show_log: true,
  show_audio: true,
  show_footer: true,
  log_min_confidence: 70,
  max_rows: 10,
  aspect_ratio: "16:9",
  emphasis: "confidence", // confidence | count
  sort: "auto", // auto (follows emphasis) | time | count | confidence
  wikipedia: true,
  wikipedia_language: "",
  tap_action: "url", // url | wikipedia | more-info | none
};

const esc = (value) =>
  String(value ?? "")
    .split("&").join("&amp;")
    .split("<").join("&lt;")
    .split(">").join("&gt;")
    .split('"').join("&quot;");

/** Only accept http(s) and internal paths. */
const safeUrl = (value) => {
  if (typeof value !== "string") return "";
  const url = value.trim();
  const lower = url.toLowerCase();
  if (lower.startsWith("http://") || lower.startsWith("https://")) return url;
  if (url.startsWith("/")) return url;
  return "";
};

/** Normalise a confidence to a percentage (accepts 0.98, 98, "98%"). */
const toPercent = (value) => {
  if (value === null || value === undefined || value === "") return null;
  const number = parseFloat(String(value).split("%").join("").split(",").join("."));
  if (Number.isNaN(number)) return null;
  return number <= 1 ? Math.round(number * 100) : Math.round(number);
};

/** Qualitative level driving the colour. A scale, not an alert code. */
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
      throw new Error("An entity is required.");
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

  getCardSize() {
    const config = this._config || DEFAULTS;
    const media =
      config.show_image && config.layout === "hero" ? 3 : 1;
    const rows = this._showsLog(config)
      ? Math.ceil((Number(config.max_rows) || 10) / 2)
      : 0;
    return media + 1 + rows;
  }

  /** The minimal layout is the compact strip on its own. */
  _showsLog(config) {
    return config.show_log && config.layout !== "minimal";
  }

  get _t() {
    return localize(this._hass);
  }

  // ------------------------------------------------------------ version check

  /**
   * A versioned URL is not enough: an already cached page (typically the
   * companion app) keeps loading the old module. So we compare the card version
   * with the one the integration reports.
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
      // Integration not installed: the card also reads plain template sensors,
      // in which case there is no version to compare.
    }
  }

  _notifyVersionMismatch(backendVersion) {
    const t = this._t;
    console.warn(
      `[birdnet-card] card ${CARD_VERSION}, integration ${backendVersion}`
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
    // The caches API requires HTTPS or localhost: fall back to a plain reload.
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

  // -------------------------------------------------------------------- data

  /** Aggregate today's log, whichever attribute shape is available. */
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

  /** Wikipedia page for a species; `force` ignores the wikipedia toggle. */
  _speciesUrl(name, force = false) {
    if ((!this._config.wikipedia && !force) || !name) return "";
    const language =
      this._config.wikipedia_language ||
      (this._hass?.locale?.language || "en").slice(0, 2);
    return `https://${language}.wikipedia.org/wiki/${encodeURIComponent(
      String(name).split(" ").join("_")
    )}`;
  }

  // ------------------------------------------------------------------ render

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
          <span>${esc(this._t.entityMissing)}: ${esc(config.entity)}</span>
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
    if (this._showsLog(config)) {
      parts.push(this._renderLog({ visibleRows, speciesCount, detectionCount, t }));
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
        ? `<span class="pill pill--${level}" title="${esc(t.confidenceTitle(confidence))}">
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

    // Large picture: the title sits on a scrim, so no vertical space is wasted.
    if (image && config.layout === "hero") {
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

    // Thumbnail or icon badge: a single 64 px band.
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

    // The highlighted column (bold value on the right plus the gauge) follows
    // the emphasis option; the other figure stays readable, just quieter.
    const byCount = config.emphasis === "count";
    const maxCount = Math.max(...visibleRows.map((row) => row.count), 1);

    // Highlighting and ordering are two separate decisions: `auto` ties them
    // together, anything else pins the order whatever is highlighted.
    const sort =
      !config.sort || config.sort === "auto"
        ? byCount
          ? "count"
          : "time"
        : config.sort;
    // Rows already arrive most recent first, so "time" needs no work.
    const ordered =
      sort === "count"
        ? [...visibleRows].sort(
            (a, b) => b.count - a.count || b.time.localeCompare(a.time)
          )
        : sort === "confidence"
          ? [...visibleRows].sort(
              (a, b) =>
                (b.confidence ?? -1) - (a.confidence ?? -1) ||
                b.time.localeCompare(a.time)
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

    // A broken picture (expired Flickr link, unreachable host) must not leave a
    // hole: fall back to the layout without media.
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

  // ----------------------------------------------------------------- actions

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

  // ------------------------------------------------------------------ styles

  static get styles() {
    return `
      :host {
        --birdnet-gap: 16px;
        --birdnet-radius: 12px;
        /* Confidence scale on a single hue, the theme's own: solid primary,
           muted primary, then grey. */
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
        /* The card measures itself: it adapts to its column, not to the
           viewport width. */
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

      /* ------------------------------------------------- media and species */
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

      /* --------------------------------------------------------------- pills */
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

      /* ----------------------------------------------------------------- log */
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

      /* ---------------------------------------------------------- responsive */
      /* Narrow column (mobile, sidebar): tighten up and let the secondary line
         wrap rather than truncating it. */
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
      /* Really narrow: totals move below the log title, nothing gets hidden. */
      @container birdnet (max-width: 260px) {
        .log__head { flex-direction: column; align-items: flex-start; gap: 2px; }
        .log__stats { white-space: normal; }
        .row__major { min-width: 0; }
      }
      /* Wide card: halve the height by laying the log out in columns. */
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

// ------------------------------------------------------------------- editor

const buildSchema = (t) => [
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
              { value: "hero", label: t.options.hero },
              { value: "compact", label: t.options.compact },
              { value: "minimal", label: t.options.minimal },
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
          { value: "confidence", label: t.options.confidence },
          { value: "count", label: t.options.count },
        ],
      },
    },
  },
  {
    name: "sort",
    selector: {
      select: {
        mode: "dropdown",
        options: [
          { value: "auto", label: t.options.sortAuto },
          { value: "time", label: t.options.sortTime },
          { value: "count", label: t.options.sortCount },
          { value: "confidence", label: t.options.sortConfidence },
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
          { value: "url", label: t.options.url },
          { value: "wikipedia", label: t.options.wikipedia },
          { value: "more-info", label: t.options.moreInfo },
          { value: "none", label: t.options.none },
        ],
      },
    },
  },
];

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
    const t = localize(this._hass);
    if (!this._form) {
      this._form = document.createElement("ha-form");
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
    this._form.computeLabel = (schema) => t.labels[schema.name] || schema.name;
    this._form.hass = this._hass;
    this._form.schema = buildSchema(t);
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
    "Latest BirdNET detection (picture, species, confidence, playback) and today's species log.",
  preview: true,
  documentationURL: "https://github.com/Pulpyyyy/ha-birdnet",
});
