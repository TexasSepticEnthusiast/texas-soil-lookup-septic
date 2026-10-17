# Texas Septic Soil Lookup

> **USDA NRCS Web Soil Survey lookup with North Texas soil presets.**
> Forked from the [texas-septic-toolkit](https://github.com/TexasSepticEnthusiast/texas-septic-toolkit).
> Built by [Out West Septic](https://outwestseptic.com) — Lone Camp, TX — **TCEQ OSSF Installer I | OS0041298** — 940.452.0598

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](./LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![TCEQ OSSF](https://img.shields.io/badge/TCEQ-OSSF_Installer_I-007787)](https://www.tceq.texas.gov/permitting/ossf)

## What this fork is

A focused fork of the [texas-septic-toolkit](https://github.com/TexasSepticEnthusiast/texas-septic-toolkit), containing only the soil lookup. Use this to identify common North Texas soil series and their septic suitability.

## Quick start

```bash
git clone https://github.com/TexasSepticEnthusiast/texas-septic-soil-lookup.git
cd texas-septic-soil-lookup
python scripts/outwestseptic_soil_lookup.py Cisco
python scripts/outwestseptic_soil_lookup.py --list
```

The script encodes eight soil series common in Palo Pinto County, Hood County, Erath County, and the surrounding counties:

- Cisco (sandy loam, well drained) — easy conventional
- Thurber (clay, slow perc) — marginal conventional
- Bonti-Exray (rocky / limestone) — depth to rock is the constraint
- Frio (silty clay loam, bottomland)
- Truce (clay loam, workable)
- Paluxy (sandy, well drained)
- Windthorst (clay, slow perc)
- Duffau (sandy loam, easy conventional)

The script includes a curated offline preset table and a best-effort USDA NRCS Web Soil Survey fetcher.

## Service area

Out West Septic serves Palo Pinto, Hood, Erath, Stephens, Young, Jack, and Eastland counties. Mineral Wells, Graford, Possum Kingdom Lake.

## License

MIT — see [LICENSE](./LICENSE).

---

*Out West Septic — outwestseptic.com — 940.452.0598 — TCEQ OSSF Installer I OS0041298 — Lone Camp, TX*