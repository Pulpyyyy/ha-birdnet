# Migrating from a trigger-based template sensor

For existing setups only. If you are installing BirdNET for the first time, you
do not need any of this — see the [README](README.md).

If you followed one of the community tutorials, you already have a `template:`
block with an `mqtt` trigger, and possibly a few `mqtt: sensor:` entries:

```yaml
template:
  - trigger:
      - platform: mqtt
        topic: "birdnet/detection"
      - platform: time
        at: "00:00:00"
        id: reset
    sensor:
      - name: "BirdNET Events"
        state: "{{ trigger.payload_json.common_name }}"
        attributes:
          bird_events: >
            ...
```

The integration replaces all of it — same topic, same fields — and adds a
persisted log, a configurable threshold and a proper automation entity.

## Steps

1. Point the card at `sensor.birdnet_last_detection` and check that it fills up.
2. Delete the `template:` block and the BirdNET `mqtt: sensor:` entries.
3. Reload templates, or restart.

Both can run side by side while you migrate: MQTT is publish/subscribe, so the
integration and your template sensor each receive their own copy of every
message, without interfering. Take your time on step 1.

## What replaces what

| Template sensor | Integration |
| --- | --- |
| `state` | `sensor.birdnet_last_detection` |
| `common_name`, `scientific_name`, `image`, `link`, `time`… attributes | Same attribute names on that sensor |
| `bird_events` attribute | `species` (per-species summary) and `detections` (full log). `bird_events` is still exposed, in the same shape, so an existing markdown card keeps working |
| `confidence_score` string | `confidence` in %, plus `confidence_score` between 0 and 1 |
| `platform: time at 00:00:00` reset | Automatic, and the log survives restarts |
| Confidence filtering inside the template | *Minimum confidence* option |
| Species exclusion inside the template | *Ignored species* option |
| — | `audio` attribute, rebuilt from the listen link |
| — | `event.birdnet_detection` for automations |

## Two things to know

Entity ids change, so any automation pointing at the old sensor has to be
updated. `event.birdnet_detection` is the entity meant for that — see the
Automation section of the [README](README.md#automation).

The history of the old sensor stays in the recorder under its own entity id. It
is not carried over, and the new sensors start from scratch.
