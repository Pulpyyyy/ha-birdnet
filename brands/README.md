# Brand assets

Home Assistant never reads an icon from the integration folder: the integrations
page always fetches it from
[brands.home-assistant.io](https://brands.home-assistant.io). A domain missing
from the [home-assistant/brands](https://github.com/home-assistant/brands)
repository shows *icon not available*.

These files are the ones to submit there, under
`custom_integrations/birdnet/`:

| File | Size |
| --- | --- |
| `icon.png` | 256 × 256 |
| `icon@2x.png` | 512 × 512 |

They are the official BirdNET logo, squared and resized from
`docs/_static/logo_birdnet_big.png` in
[birdnet-team/BirdNET-Analyzer](https://github.com/birdnet-team/BirdNET-Analyzer).

BirdNET is a project of the K. Lisa Yang Center for Conservation Bioacoustics at
the Cornell Lab of Ornithology, in collaboration with Chemnitz University of
Technology. The logo is reproduced here only to identify the service this
integration talks to. This integration is not affiliated with, nor endorsed by,
either institution.
