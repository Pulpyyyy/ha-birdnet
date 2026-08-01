# BirdNET pour Home Assistant

Intégration **et** carte Lovelace pour exploiter les détections d'oiseaux publiées
sur MQTT par [BirdNET-Pi](https://github.com/Nachtzuster/BirdNET-Pi) (via Apprise)
ou [BirdNET-Go](https://github.com/tphakala/birdnet-go).

Fini le template sensor à déclencheur, la pile `stack-in-card` + `mushroom` +
`markdown` : une intégration qui écoute le topic, tient le journal de la journée,
et une seule carte qui affiche tout.

## Ce que ça apporte

| Entité | Description |
| --- | --- |
| `sensor.birdnet_derniere_detection` | Nom commun de la dernière espèce, plus tous les détails en attributs (photo, lien, confiance, journal du jour, résumé par espèce) |
| `sensor.birdnet_confiance` | Confiance de la dernière détection, en % |
| `sensor.birdnet_heure_de_detection` | Horodatage (`device_class: timestamp`) |
| `sensor.birdnet_detections_du_jour` | Nombre de détections depuis minuit |
| `sensor.birdnet_especes_du_jour` | Nombre d'espèces distinctes + détail par espèce |
| `image.birdnet_derniere_detection` | Photo de l'espèce, utilisable dans `picture-entity` |
| `event.birdnet_detection` | Déclencheur d'automatisation propre, une fois par détection |

Plus deux services : `birdnet.simulate_detection` (pour tester la carte sans
attendre un oiseau) et `birdnet.clear_log`.

Le journal du jour est **persisté** : un redémarrage de Home Assistant ne le vide
plus. Il est remis à zéro à minuit, et exclu du recorder pour ne pas gonfler la
base.

## Installation

### HACS (recommandé)

1. HACS → Intégrations → menu ⋮ → *Dépôt personnalisé*
2. URL du dépôt, catégorie **Integration**
3. Installer *BirdNET*, puis redémarrer Home Assistant
4. Paramètres → Appareils et services → *Ajouter une intégration* → **BirdNET**

### Manuelle

Copier `custom_components/birdnet` dans `config/custom_components/`, redémarrer,
puis ajouter l'intégration.

La carte est **livrée avec l'intégration** : elle est servie sur
`/birdnet_frontend/birdnet-card.js` et ajoutée automatiquement aux ressources
Lovelace (dashboards en mode interface). En mode YAML, ajoutez :

```yaml
lovelace:
  resources:
    - url: /birdnet_frontend/birdnet-card.js
      type: module
```

## Configuration

À l'ajout de l'intégration :

| Champ | Défaut | Rôle |
| --- | --- | --- |
| Topic MQTT | `birdnet/detection` | Topic sur lequel BirdNET publie |
| Confiance minimale | 70 % | En dessous, la détection est ignorée |
| Espèces ignorées | — | Nom commun ou scientifique (ex. `Humain`, `Bruit`) |

Modifiable ensuite par le bouton *Configurer*, avec en plus le nombre de
détections conservées par jour (500 par défaut).

### Formats de payload acceptés

Le parseur normalise les clés, il accepte donc indifféremment :

```json
{ "common_name": "Pie bavarde", "scientific_name": "Pica pica",
  "confidence_score": "0.9871", "date": "2026-08-01", "time": "22:06:15",
  "link": "http://birdpi/?filename=Pie_bavarde-99-2026-08-01-birdnet-22:06:15.mp3",
  "image": "https://upload.wikimedia.org/..." }
```

```json
{ "CommonName": "Eurasian Magpie", "ScientificName": "Pica pica",
  "Confidence": 0.9871, "Date": "2026-08-01", "Time": "22:06:15",
  "BirdImage": { "URL": "https://..." } }
```

Le modèle Apprise à coller dans BirdNET-Pi (Services de notification → corps du
message) :

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

Quand le lien contient `?filename=xxx.mp3`, l'URL du clip audio BirdNET-Pi est
reconstruite (`/By_Date/<date>/<Espece>/<fichier>`) et exposée dans l'attribut
`audio` : la carte affiche alors un lecteur.

## La carte

```yaml
type: custom:birdnet-card
entity: sensor.birdnet_derniere_detection
```

Toutes les options (éditeur visuel disponible) :

```yaml
type: custom:birdnet-card
entity: sensor.birdnet_derniere_detection
title: Oiseaux du jardin      # optionnel
layout: hero                  # hero (grande photo) | compact (vignette 56 px)
aspect_ratio: "16:9"          # format de la photo
show_image: true              # photo de l'espèce
show_chips: true              # nom scientifique + pastille de fiabilité
show_audio: true              # bouton de lecture du clip, si disponible
show_log: true                # journal des espèces du jour
show_footer: true             # totaux (espèces / détections)
log_min_confidence: 70        # seuil d'affichage dans le journal
max_rows: 10                  # lignes du journal
wikipedia: true               # nom d'espèce cliquable vers Wikipédia
wikipedia_language: fr        # par défaut : langue de l'utilisateur
tap_action: url               # url | more-info | none
```

### Parti pris de design

* **Photo en fond, texte en incrustation.** Le nom, le nom latin, l'heure et la
  fiabilité tiennent sur la photo : trois lignes de carte économisées, aucune
  information perdue.
* **Fiabilité lisible d'un coup d'œil.** Pastille colorée sur une échelle de
  confiance (≥ 90 %, ≥ 75 %, en dessous) et micro-jauge sous chaque ligne du
  journal. Une seule teinte, celle du thème : couleur primaire franche, primaire
  atténuée, puis gris — pas un code d'alerte, une échelle, et la carte suit
  automatiquement tes couleurs.
* **Journal dense.** Une ligne par espèce : heure, nom cliquable, nombre de
  détections, meilleure fiabilité. Chiffres en chasse fixe pour un alignement
  net. Les totaux du jour sont dans l'en-tête de section, pas sur une ligne
  supplémentaire.
* **Écoute sur place.** Quand le clip est disponible, un bouton de lecture
  discret remplace le lecteur `<audio>` natif (30 px au lieu de 54, et il suit
  le thème).
* **Vraiment responsive.** La carte se mesure elle-même (*container queries*) :
  elle s'adapte à la largeur de **sa colonne**, pas à celle de l'écran. En
  colonne étroite elle se resserre et laisse respirer, au-delà de 520 px le
  journal passe sur deux colonnes (trois au-delà de 760 px) pour diviser la
  hauteur par deux.
* **Accessible.** Zones cliquables au clavier avec anneau de focus, libellés
  ARIA sur le bouton de lecture, animations désactivées si
  `prefers-reduced-motion`, image cassée → repli automatique sans trou dans la
  mise en page.

### Compatibilité avec un template sensor existant

La carte sait aussi lire un capteur du type de ceux du tuto HACF (attributs
`common_name`, `image`, `link`, `confidence_score`, `bird_events`) :

```yaml
type: custom:birdnet-card
entity: sensor.birdnet_go_events
```

Elle fonctionne donc avant même de basculer sur l'intégration. Inversement,
`sensor.birdnet_derniere_detection` expose un attribut `bird_events` au même
format, pour ne pas casser une carte markdown existante.

## Automatisation

```yaml
triggers:
  - trigger: state
    entity_id: event.birdnet_detection
conditions:
  - condition: template
    value_template: "{{ trigger.to_state.attributes.common_name == 'Chouette hulotte' }}"
actions:
  - action: notify.mobile_app
    data:
      title: "{{ trigger.to_state.attributes.common_name }}"
      message: >-
        {{ trigger.to_state.attributes.confidence }} % à
        {{ trigger.to_state.attributes.time }}
      data:
        image: "{{ trigger.to_state.attributes.image }}"
```

## Dépannage

* Rien ne remonte → activez le capteur de diagnostic *Topic MQTT* : il compte les
  messages reçus et affiche la dernière erreur de parsing.
* Vérifiez le topic avec `mosquitto_sub -h <broker> -t 'birdnet/#' -v`.
* Détections filtrées → baissez la confiance minimale dans les options.
* La carte n'apparaît pas dans la liste → videz le cache du navigateur, et
  vérifiez la ressource dans Paramètres → Tableaux de bord → menu ⋮ → Ressources.

## Crédits

Format du payload et logique du tableau inspirés du
[tuto BirdNET de la communauté HACF](https://forum.hacf.fr/t/birdnet-tuto-comment-reperer-et-ecouter-les-oiseaux-du-jardin/66856).

Mécanisme d'embarquement de la carte dans l'intégration (chemin statique,
ressource Lovelace, contrôle de version anti-cache) repris du
[guide développeur de KipK](https://forum.hacf.fr/t/guide-developpeur-carte-lovelace-embarquee-dans-une-integration-home-assistant/74074),
tiré de l'intégration [marees_france](https://github.com/KipK/marees_france).
