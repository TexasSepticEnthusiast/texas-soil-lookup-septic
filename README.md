# USDA soil survey lookup for the Out West Septic project

Retrieve published SSURGO map-unit components from USDA Soil Data Access. This tool supports background research for the [Out West Septic](https://outwestseptic.com) project, with Palo Pinto County as the worked example. It does not infer septic suitability or identify the soil at a specific point.

## Run

Python 3.10+; standard library only. A live lookup requires internet access.

```sh
git clone https://github.com/TexasSepticEnthusiast/texas-soil-lookup-septic.git
cd texas-soil-lookup-septic
python scripts/outwestseptic_soil_lookup.py --mukey 390929
python scripts/outwestseptic_soil_lookup.py --mukey 390929 --json
python -m unittest discover -s tests -v
```

The example key was returned by USDA for survey `TX363` (Palo Pinto County) on 2026-10-18. It is an example map unit, not a customer property or a recommendation. Use the key for your own area of interest.

## Find the right key

1. Open [USDA Web Soil Survey](https://websoilsurvey.nrcs.usda.gov/app/), locate the property and define an area of interest.
2. Inspect the soil map and map-unit information. Obtain the numeric national map-unit key (`mukey`), not a soil series name or the survey-local map symbol (`musym`). USDA's [query guide](https://sdmdataaccess.nrcs.usda.gov/documents/FundamentalQuery.pdf) explains these distinct identifiers and national map-unit labels.
3. Query each relevant map unit. Check the returned survey name, key and map-unit description against the map. A property can contain more than one map unit.
4. Save the JSON output with the project record. It includes the survey version date as reported by USDA, retrieval time, source endpoint and limitations.

## Interpret the output

The report lists mapped components, their representative share and drainage class. These are survey attributes, not field measurements. Component shares are not normalized; missing percentages or drainage classes remain `null` in JSON and `not reported` in text. A map unit may have no component records.

The report deliberately supplies no percolation rate, bedrock depth, hydraulic loading rate, system selection or pass/fail decision. USDA explains that survey information supports planning and that engineering applications can require onsite investigation. The permitting authority and qualified site evaluator must determine what applies to the property.

## Errors and migration

The command returns `0` for a usable report, `1` for a failed lookup or missing/malformed data, and `2` for invalid input. A service outage never falls back to guessed values. `--timeout` accepts a finite value greater than zero and at most 60 seconds (default 20).

This replaces the old `Cisco`, `--list` and `--try-usda COUNTY` interface and removes `SOIL_PRESETS`, `lookup_series` and `list_series`. Those paths previously supplied uncited rates and a county-download request whose results were never parsed. Python callers now use `OutWestSepticSoilLookup.fetch_usda(mukey)` and receive `SoilMapUnit` or an explicit exception. There is no hidden compatibility path that returns the old guesses.

## Sources and contribution

Reviewed 2026-10-18:

- [USDA REST service documentation](https://sdmdataaccess.nrcs.usda.gov/webservicehelp.aspx): POST query service and JSON column-name format.
- [USDA fundamental query](https://sdmdataaccess.nrcs.usda.gov/documents/FundamentalQuery.pdf): map-unit/component relationships and survey version metadata.
- [USDA SSURGO versus STATSGO](https://sdmdataaccess.nrcs.usda.gov/documents/DiscriminatingBetweenSSURGOAndSTATSGO.pdf): SSURGO query constraint.
- [USDA Web Soil Survey](https://websoilsurvey.nrcs.usda.gov/app/): map selection and onsite-investigation limits.

This revision is an AI-assisted contribution requested for the Out West Septic project. It does not claim independent endorsement, licensed design review, field use or business credentials. See [LICENSE](LICENSE) and the [reference notes](wiki/Soil-Lookup-Reference.md).
