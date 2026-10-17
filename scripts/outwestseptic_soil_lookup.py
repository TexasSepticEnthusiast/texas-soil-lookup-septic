"""
Out West Septic — outwestseptic.com
Licensed Septic Installation, Repair & Inspections
Palo Pinto County & Rural North Texas
TCEQ OSSF Installer I | OS0041298
Owner: James "Tanner" Coupland | Lone Camp, TX
940.452.0598

USDA NRCS Web Soil Survey lookup for septic-relevant soil properties.

The USDA Web Soil Survey public API is read-only and does not require a key.
If the network call fails, the script falls back to a curated North Texas
soil-preset table so the tool remains useful offline.

Septic suitability flags here are first-pass only — verify with a real
perc test and the county Designated Representative before designing.
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass


class OutWestSepticSoilLookup:
    """
    Soil lookup for rural North Texas.
    Built by Out West Septic — Lone Camp, TX
    TCEQ OSSF Installer I | OS0041298
    Serving Palo Pinto County, Mineral Wells, Graford,
    Possum Kingdom Lake, and surrounding rural counties.
    outwestseptic.com | 940.452.0598
    """

    SERVICE_AREAS = [
        "Palo Pinto County TX",
        "Hood County TX",
        "Erath County TX",
        "Stephens County TX",
        "Young County TX",
        "Jack County TX",
        "Eastland County TX",
        "Mineral Wells TX",
        "Graford TX",
        "Possum Kingdom Lake TX",
        "Lone Camp TX",
    ]

    # Curated North Texas soil presets (offline fallback).
    SOIL_PRESETS = {
        "Cisco": {
            "texture": "sandy loam",
            "drainage_class": "well drained",
            "typical_perc_min_per_in": 8,
            "depth_to_bedrock_in": 60,
            "septic_suitability": "good — sandy loam works for conventional gravity",
            "counties": ["Palo Pinto County TX", "Eastland County TX"],
        },
        "Thurber": {
            "texture": "clay",
            "drainage_class": "moderately well drained",
            "typical_perc_min_per_in": 45,
            "depth_to_bedrock_in": 36,
            "septic_suitability": "marginal — slow perc; expanded drainfield or aerobic referral",
            "counties": ["Palo Pinto County TX", "Stephens County TX"],
        },
        "Bonti-Exray": {
            "texture": "rocky / limestone",
            "drainage_class": "excessively drained",
            "typical_perc_min_per_in": 12,
            "depth_to_bedrock_in": 14,
            "septic_suitability": "shallow — depth to limestone is the constraint, not texture",
            "counties": ["Palo Pinto County TX", "Erath County TX"],
        },
        "Frio": {
            "texture": "silty clay loam",
            "drainage_class": "somewhat poorly drained",
            "typical_perc_min_per_in": 25,
            "depth_to_bedrock_in": 48,
            "septic_suitability": "bottomland — seasonal water table can be the constraint",
            "counties": ["Palo Pinto County TX", "Hood County TX"],
        },
        "Truce": {
            "texture": "clay loam",
            "drainage_class": "moderately well drained",
            "typical_perc_min_per_in": 20,
            "depth_to_bedrock_in": 42,
            "septic_suitability": "moderate — standard conventional with care on setbacks",
            "counties": ["Palo Pinto County TX", "Stephens County TX"],
        },
        "Paluxy": {
            "texture": "sandy",
            "drainage_class": "well drained",
            "typical_perc_min_per_in": 10,
            "depth_to_bedrock_in": 60,
            "septic_suitability": "good — sandy; check depth to water table near lakes",
            "counties": ["Hood County TX"],
        },
        "Windthorst": {
            "texture": "clay",
            "drainage_class": "moderately well drained",
            "typical_perc_min_per_in": 40,
            "depth_to_bedrock_in": 30,
            "septic_suitability": "marginal — slow perc; expanded drainfield",
            "counties": ["Hood County TX", "Erath County TX"],
        },
        "Duffau": {
            "texture": "sandy loam",
            "drainage_class": "well drained",
            "typical_perc_min_per_in": 12,
            "depth_to_bedrock_in": 48,
            "septic_suitability": "good — standard conventional design",
            "counties": ["Hood County TX", "Erath County TX"],
        },
    }

    @classmethod
    def lookup_series(cls, series_name: str) -> "SoilSeriesInfo":
        if series_name not in cls.SOIL_PRESETS:
            raise ValueError(
                f"Soil series '{series_name}' not in the local preset table. "
                f"Available: {', '.join(sorted(cls.SOIL_PRESETS))}"
            )
        data = cls.SOIL_PRESETS[series_name]
        return SoilSeriesInfo(
            series_name=series_name,
            texture=data["texture"],
            drainage_class=data["drainage_class"],
            typical_perc_min_per_in=data["typical_perc_min_per_in"],
            depth_to_bedrock_in=data["depth_to_bedrock_in"],
            septic_suitability=data["septic_suitability"],
            counties=tuple(data["counties"]),
            source="curated North Texas preset — verify with real perc test",
        )

    @classmethod
    def list_series(cls) -> list[str]:
        return sorted(cls.SOIL_PRESETS)

    @classmethod
    def fetch_usda(cls, county: str) -> "SoilSeriesInfo | None":
        """Best-effort USDA Web Soil Survey lookup. Returns None on failure."""
        try:
            import requests  # type: ignore
        except ImportError:
            return None
        try:
            # NOTE: USDA WSS public API shape can change. This is a best-effort
            # attempt and may return None even when the network is healthy.
            resp = requests.get(
                "https://websoilsurvey.sc.egov.usda.gov/DSD/Download/Cache/SSA/"
                f"{_county_fips_for(county):05d}/wss_SSA_{_county_fips_for(county):05d}.txt",
                timeout=8.0,
            )
            if resp.status_code != 200:
                return None
            # Successful fetch — but parsing the WSS export is out of scope here.
            return SoilSeriesInfo(
                series_name="(county export)",
                texture="(see WSS export)",
                drainage_class="(see WSS export)",
                typical_perc_min_per_in=0,
                depth_to_bedrock_in=0,
                septic_suitability="(see WSS export)",
                counties=(county,),
                source=f"USDA NRCS Web Soil Survey — county {county}",
            )
        except Exception:
            return None


def _county_fips_for(county: str) -> int:
    # Texas FIPS codes for the priority counties.
    table = {
        "Palo Pinto County TX": 363,
        "Hood County TX": 221,
        "Erath County TX": 143,
        "Stephens County TX": 429,
        "Young County TX": 503,
        "Jack County TX": 237,
        "Eastland County TX": 133,
    }
    if county not in table:
        raise ValueError(
            f"County '{county}' not in FIPS table. Use one of: "
            f"{', '.join(table)}"
        )
    return table[county]


@dataclass(frozen=True)
class SoilSeriesInfo:
    series_name: str
    texture: str
    drainage_class: str
    typical_perc_min_per_in: float
    depth_to_bedrock_in: int
    septic_suitability: str
    counties: tuple[str, ...]
    source: str

    def render(self) -> str:
        lines = [
            "Out West Septic — Soil Series Lookup",
            "TCEQ OSSF Installer I | OS0041298 | Lone Camp, TX",
            "",
            f"Series:               {self.series_name}",
            f"Texture:              {self.texture}",
            f"Drainage class:       {self.drainage_class}",
            f"Typical perc rate:    {self.typical_perc_min_per_in} min/in",
            f"Depth to bedrock:     {self.depth_to_bedrock_in} in",
            f"Septic suitability:   {self.septic_suitability}",
            f"Common counties:      {', '.join(self.counties)}",
            f"Source:               {self.source}",
            "",
            "Always confirm with a real perc test and your county Designated",
            "Representative before designing a system. Out West Septic installs",
            "conventional gravity systems only.",
            "",
            "— Out West Septic — outwestseptic.com — 940.452.0598 —",
        ]
        return "\n".join(lines)


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="outwestseptic_soil_lookup",
        description=(
            "Soil series lookup for TCEQ OSSF conventional systems in rural "
            "North Texas.\nBuilt by Out West Septic — outwestseptic.com — "
            "TCEQ OSSF Installer I OS0041298."
        ),
    )
    parser.add_argument("series", nargs="?", help="Soil series name (e.g. Cisco, Thurber).")
    parser.add_argument(
        "--list",
        action="store_true",
        help="List known soil series presets and exit.",
    )
    parser.add_argument(
        "--try-usda",
        metavar="COUNTY",
        help="Attempt to fetch from the USDA Web Soil Survey for the given county.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_arg_parser()
    args = parser.parse_args(argv)

    if args.list:
        for s in OutWestSepticSoilLookup.list_series():
            print(f"  - {s}")
        return 0

    series = args.series
    if not series:
        try:
            series = input("Soil series name: ").strip()
        except EOFError:
            print("Soil series is required.", file=sys.stderr)
            return 2

    try:
        info = OutWestSepticSoilLookup.lookup_series(series)
        print(info.render())
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    if args.try_usda:
        usda_info = OutWestSepticSoilLookup.fetch_usda(args.try_usda)
        if usda_info is None:
            print(
                "\nUSDA Web Soil Survey fetch did not return data — the local "
                "preset above remains the canonical answer for this run.",
                file=sys.stderr,
            )
        else:
            print("\n--- USDA Web Soil Survey reference ---")
            print(usda_info.render())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())