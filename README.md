# BirdNET for Home Assistant

A Home Assistant integration **and** its Lovelace card for the bird detections
published over MQTT by [BirdNET-Pi](https://github.com/Nachtzuster/BirdNET-Pi)
(through Apprise) or [BirdNET-Go](https://github.com/tphakala/birdnet-go).

No more trigger-based template sensor, no more `stack-in-card` + `mushroom` +
`markdown` pile: an integration that listens to the topic and keeps the daily
log, and a single card that shows all of it.

## What you get

| Entity | Description |
| --- | --- |
| `sensor.birdnet_last_detection` | Common name of the latest species, plus every detail as attributes (picture, link, confidence, daily log, per-species summary) |
| `sensor.birdnet_confidence` | Confidence of the latest detection, in % |
| `sensor.birdnet_detection_time` | Timestamp (`device_class: timestamp`) |
| `sensor.birdnet_detections_today` | Number of detections since midnight |
| `sensor.birdnet_species_today` | Number of distinct species, with a per-species breakdown |
| `image.birdnet_last_detection` | Species picture, usable in a `picture-entity` card |
| `event.birdnet_detection` | A clean automation trigger, fired once per detection |

Plus two services: `birdnet.simulate_detection` (to test the card without
waiting for a bird) and `birdnet.clear_log`.

The daily log is **persisted**: restarting Home Assistant no longer wipes it. It
resets at midnight and is excluded from the recorder so it does not bloat the
database.

## Installation

### HACS (recommended)

1. HACS → Integrations → ⋮ menu → *Custom repositories*
2. Repository URL, category **Integration**
3. Install *BirdNET*, then restart Home Assistant
4. Settings → Devices & services → *Add integration* → **BirdNET**

### Manual

Copy `custom_components/birdnet` into `config/custom_components/`, restart, then
add the integration.

The card **ships with the integration**: it is served from
`/birdnet_frontend/birdnet-card.js` and registered automatically in the Lovelace
resources (storage-mode dashboards). In YAML mode, add it yourself:

```yaml
lovelace:
  resources:
    - url: /birdnet_frontend/birdnet-card.js
      type: module
```

## Configuration

When adding the integration:

| Field | Default | Purpose |
| --- | --- | --- |
| MQTT topic | `birdnet/detection` | The topic BirdNET publishes to |
| Minimum confidence | 70 % | Anything below is discarded |
| Ignored species | — | Common or scientific name (e.g. `Human`, `Noise`) |

All of it can be changed later through *Configure*, along with the number of
detections kept per day (500 by default).

### Accepted payloads

The parser normalises keys, so all of these work:

```json
{ "common_name": "Eurasian Magpie", "scientific_name": "Pica pica",
  "confidence_score": "0.9871", "date": "2026-08-01", "time": "22:06:15",
  "link": "http://birdpi/?filename=Eurasian_Magpie-99-2026-08-01-birdnet-22:06:15.mp3",
  "image": "https://upload.wikimedia.org/..." }
```

```json
{ "CommonName": "Eurasian Magpie", "ScientificName": "Pica pica",
  "Confidence": 0.9871, "Date": "2026-08-01", "Time": "22:06:15",
  "BirdImage": { "URL": "https://..." } }
```

The Apprise template to paste into BirdNET-Pi (Notification services → message
body):

```json
{
  "common_name": "$comname",
  "scientific_name": "$sciname",
  "confidence_score": "$confidence",
  "link": "$listenurl",
  "date": "$date",
  "time": "$time",
  "week": "$week",
  "latitude": "$latitude",
  "longitude": "$longitude",
  "minimum_confidence": "$cutoff",
  "sigmoid_sensitivity": "$sens",
  "overlap": "$overlap",
  "image": "$flickrimage"
}
```

When the link carries a `?filename=xxx.mp3` query, the BirdNET-Pi audio clip URL
is rebuilt (`/By_Date/<date>/<Species>/<file>`) and exposed as the `audio`
attribute — the card then shows a play button.

## The card

```yaml
type: custom:birdnet-card
entity: sensor.birdnet_last_detection
```

Every option (a visual editor is available):

```yaml
type: custom:birdnet-card
entity: sensor.birdnet_last_detection
title: Garden birds          # optional
layout: hero                 # hero (large picture) | compact (56 px thumbnail)
aspect_ratio: "16:9"         # picture aspect ratio
show_image: true             # species picture
show_chips: true             # scientific name + confidence pill
show_audio: true             # play button for the clip, when available
show_log: true               # today's species log
show_footer: true            # totals (species / detections)
log_min_confidence: 70       # display threshold for the log
max_rows: 10                 # log rows
emphasis: confidence         # confidence | count: what the log highlights
wikipedia: true              # species names link to Wikipedia
wikipedia_language: en       # defaults to the user's language
tap_action: url              # url | wikipedia | more-info | none
```

`emphasis` switches the bold figure on the right and the gauge: `confidence`
highlights the best confidence for the species, `count` its number of detections
(the gauge then becomes relative to the most heard species, and the log is
sorted by descending count). The other figure stays visible, just quieter.

`tap_action: url` opens the BirdNET link from the MQTT message, falling back to
Wikipedia when it is missing; `wikipedia` always goes to Wikipedia.

### Design notes

* **Picture as a backdrop, text on top.** Name, scientific name, time and
  confidence sit on the picture: three card rows saved, no information lost.
* **Confidence readable at a glance.** A coloured pill on a confidence scale
  (≥ 90 %, ≥ 75 %, below) and a micro gauge under each log row. A single hue,
  the theme's own: solid primary, muted primary, then grey — a scale, not an
  alert code, and the card follows your colours.
* **Dense log.** One row per species: time, clickable name, number of
  detections, best confidence. Tabular figures for clean alignment. Daily totals
  live in the section header rather than on an extra row.
* **Listen in place.** When the clip is available, a discreet play button
  replaces the native `<audio>` player (30 px instead of 54, and it follows the
  theme).
* **Genuinely responsive.** The card measures itself (*container queries*): it
  adapts to the width of **its column**, not of the screen. In a narrow column
  it tightens up; past 520 px the log moves to two columns (three past 760 px),
  halving its height.
* **Accessible.** Keyboard-reachable tap targets with a focus ring, ARIA labels
  on the play button, animations disabled under `prefers-reduced-motion`, and a
  broken picture falls back without leaving a hole in the layout.

### Working with an existing template sensor

The card also reads sensors of the kind found in community tutorials
(`common_name`, `image`, `link`, `confidence_score`, `bird_events` attributes):

```yaml
type: custom:birdnet-card
entity: sensor.birdnet_go_events
```

So it works before you switch to the integration. Conversely,
`sensor.birdnet_last_detection` exposes a `bird_events` attribute in the same
shape, so an existing markdown card keeps working.

## Coming from a trigger-based template sensor

If you followed one of the community tutorials, you already have a `template:`
block with an `mqtt` trigger, and possibly a few `mqtt: sensor:` entries. The
integration replaces all of it — same topic, same fields — and adds a persisted
log, a configurable threshold and a proper automation entity.

1. Point the card at `sensor.birdnet_last_detection` and check that it fills up.
2. Delete the `template:` block and the BirdNET `mqtt: sensor:` entries.
3. Reload templates, or restart.

Both can run side by side while you migrate: MQTT is publish/subscribe, so the
integration and your template sensor each receive their own copy of every
message, without interfering.

Two things to know. Entity ids change, so any automation pointing at the old
sensor has to be updated — `event.birdnet_detection` is the entity meant for
that, see [Automation](#automation). And the history of the old sensor stays in
the recorder, it is not carried over.

## Languages

Everything the user sees follows the Home Assistant user language, in **English,
French, German, Spanish and Italian**: the setup and options dialogs, entity
names, service names and descriptions, and the card together with its visual
editor. Anything else falls back to English.

## Automation

```yaml
triggers:
  - trigger: state
    entity_id: event.birdnet_detection
conditions:
  - condition: template
    value_template: "{{ trigger.to_state.attributes.common_name == 'Tawny Owl' }}"
actions:
  - action: notify.mobile_app
    data:
      title: "{{ trigger.to_state.attributes.common_name }}"
      message: >-
        {{ trigger.to_state.attributes.confidence }} % at
        {{ trigger.to_state.attributes.time }}
      data:
        image: "{{ trigger.to_state.attributes.image }}"
```

## Troubleshooting

* Nothing shows up → enable the *MQTT topic* diagnostic sensor: it counts
  received messages and reports the last parsing error.
* Check the topic with `mosquitto_sub -h <broker> -t 'birdnet/#' -v`.
* Detections filtered out → lower the minimum confidence in the options.
* The card is missing from the picker → clear the browser cache and check the
  resource under Settings → Dashboards → ⋮ → Resources.

## Credits

Payload format and log layout inspired by the
[BirdNET tutorial from the HACF community](https://forum.hacf.fr/t/birdnet-tuto-comment-reperer-et-ecouter-les-oiseaux-du-jardin/66856).

The card embedding mechanism (static path, Lovelace resource, anti-cache version
check) follows
[KipK's developer guide](https://forum.hacf.fr/t/guide-developpeur-carte-lovelace-embarquee-dans-une-integration-home-assistant/74074),
drawn from the [marees_france](https://github.com/KipK/marees_france)
integration.
