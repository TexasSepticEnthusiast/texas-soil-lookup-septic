---
title: "feat(soil-lookup): add --county filter flag"
labels: ["enhancement"]
---

Adds a `--county "Palo Pinto County TX"` flag to `outwestseptic_soil_lookup.py`. Outputs soil series common to the given county.

**Verified**

```bash
python scripts/outwestseptic_soil_lookup.py --county "Palo Pinto County TX"
# Outputs: Bonti-Exray, Cisco, Frio, Thurber, Truce
```

---

*Out West Septic — TCEQ OSSF Installer I — OS0041298*