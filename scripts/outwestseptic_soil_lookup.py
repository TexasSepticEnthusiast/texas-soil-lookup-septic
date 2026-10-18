"""Read SSURGO map-unit components from USDA Soil Data Access.

Maintained as an automated contribution to the Out West Septic project.
Survey information is background research, not a parcel evaluation or OSSF design.
"""
from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from http.client import HTTPException
import json
import math
import re
import sys
from urllib.error import URLError
from urllib.request import Request, urlopen

ENDPOINT = "https://sdmdataaccess.nrcs.usda.gov/Tabular/post.rest"
WSS = "https://websoilsurvey.nrcs.usda.gov/app/"
LIMITATION = (
    "Survey map units describe an area containing multiple components; they do not "
    "identify the soil at an exact point. No percolation rate, loading rate, system "
    "suitability, or permit approval is inferred. Obtain a site evaluation."
)
COLUMNS = (
    "areasymbol", "areaname", "saverest", "mukey", "musym", "muname",
    "cokey", "compname", "comppct_r", "drainagecl",
)
MAX_RESPONSE_BYTES = 2 * 1024 * 1024


class OutWestSepticSoilDataError(RuntimeError):
    """The official service did not return usable survey data."""


SoilDataError = OutWestSepticSoilDataError


def validate_mukey(value: str) -> str:
    """Require a numeric USDA key; never interpolate caller-supplied SQL."""
    if not isinstance(value, str) or not re.fullmatch(r"[1-9][0-9]{0,29}", value):
        raise ValueError("mukey must be a positive ASCII integer key from Web Soil Survey.")
    return value


def build_query(mukey: str) -> str:
    key = validate_mukey(mukey)
    return f"""SELECT l.areasymbol, l.areaname, sac.saverest,
       m.mukey, m.musym, m.muname,
       c.cokey, c.compname, c.comppct_r, c.drainagecl
FROM mapunit AS m
INNER JOIN legend AS l ON m.lkey = l.lkey
    AND l.areatypename = 'Non-MLRA Soil Survey Area'
INNER JOIN sacatalog AS sac ON sac.areasymbol = l.areasymbol
LEFT JOIN component AS c ON c.mukey = m.mukey
WHERE m.mukey = '{key}'
ORDER BY c.comppct_r DESC, c.cokey"""


@dataclass(frozen=True)
class OutWestSepticSoilComponent:
    key: str
    name: str | None
    representative_percent: int | None
    drainage_class: str | None


@dataclass(frozen=True)
class OutWestSepticSoilMapUnit:
    mukey: str
    symbol: str
    name: str
    survey_area: str
    survey_name: str
    survey_version_date: str | None
    components: tuple[OutWestSepticSoilComponent, ...]
    retrieved_at: str
    source: str = ENDPOINT
    limitation: str = LIMITATION

    def render(self) -> str:
        lines = [
            "Out West Septic project - USDA soil survey reference",
            f"Map unit: {self.mukey} / {self.symbol} - {self.name}",
            f"Survey: {self.survey_area} - {self.survey_name}",
            f"Survey version date: {self.survey_version_date or 'not reported'}",
            f"Retrieved (UTC): {self.retrieved_at}",
            f"Source: {self.source}", "", "Mapped components:",
        ]
        for component in self.components:
            percent = ("not reported" if component.representative_percent is None
                       else f"{component.representative_percent}%")
            lines.append(
                f"- {component.name or 'name not reported'} (key {component.key}): "
                f"representative share {percent}; drainage "
                f"{component.drainage_class or 'not reported'}"
            )
        if not self.components:
            lines.append("- No component records reported; this is not an approval.")
        lines.extend(["", self.limitation, f"Check the map and full report: {WSS}"])
        return "\n".join(lines)


SoilComponent = OutWestSepticSoilComponent
SoilMapUnit = OutWestSepticSoilMapUnit


def _optional_text(value: object) -> str | None:
    if value is None or value == "":
        return None
    if not isinstance(value, str):
        raise SoilDataError("USDA returned an unexpected text field.")
    return value


def _required_text(value: object) -> str:
    text = _optional_text(value)
    if text is None:
        raise SoilDataError("USDA omitted a required map-unit identifier.")
    return text


def _percentage(value: object) -> int | None:
    if value is None or value == "":
        return None
    if isinstance(value, bool) or not re.fullmatch(r"[0-9]{1,3}", str(value)):
        raise SoilDataError("USDA returned an invalid component percentage.")
    percent = int(value)
    if percent > 100:
        raise SoilDataError("USDA returned a component percentage above 100.")
    return percent


def parse_response(payload: object, mukey: str) -> SoilMapUnit:
    key = validate_mukey(mukey)
    if not isinstance(payload, dict) or "Table" not in payload:
        raise SoilDataError("USDA returned no result table; no local data were substituted.")
    table = payload["Table"]
    if not isinstance(table, list) or len(table) < 2:
        raise SoilDataError(f"No SSURGO map unit returned for mukey {key}.")
    header = table[0]
    if (not isinstance(header, list) or any(not isinstance(c, str) for c in header)
            or len(set(header)) != len(header) or not set(COLUMNS).issubset(header)):
        raise SoilDataError("USDA response columns do not match the expected schema.")
    metadata = None
    components = []
    seen_keys = set()
    for row in table[1:]:
        if not isinstance(row, list) or len(row) != len(header):
            raise SoilDataError("USDA returned a malformed table row.")
        item = dict(zip(header, row))
        row_meta = tuple(item[c] for c in COLUMNS[:6])
        if item["mukey"] != key or (metadata is not None and row_meta != metadata):
            raise SoilDataError("USDA returned inconsistent map-unit identifiers.")
        metadata = row_meta
        if item["cokey"] is None or item["cokey"] == "":
            if any(item[c] not in (None, "") for c in COLUMNS[7:]):
                raise SoilDataError("USDA returned component data without a key.")
            continue
        component_key = _required_text(item["cokey"])
        if component_key in seen_keys:
            raise SoilDataError("USDA returned a duplicate component key.")
        seen_keys.add(component_key)
        components.append(SoilComponent(
            component_key, _optional_text(item["compname"]),
            _percentage(item["comppct_r"]), _optional_text(item["drainagecl"]),
        ))
    area, area_name, version, _, symbol, name = metadata
    return SoilMapUnit(
        key, _required_text(symbol), _required_text(name), _required_text(area),
        _required_text(area_name), _optional_text(version), tuple(components),
        datetime.now(timezone.utc).isoformat(),
    )


class OutWestSepticSoilLookup:
    """Fetch published survey components without inventing site measurements."""

    @staticmethod
    def fetch_usda(mukey: str, timeout: float = 20.0) -> SoilMapUnit:
        query = build_query(mukey)
        if (isinstance(timeout, bool) or not isinstance(timeout, (float, int))
                or not 0 < timeout <= 60 or not math.isfinite(timeout)):
            raise ValueError("timeout must be finite and between 0 and 60 seconds.")
        body = json.dumps({"query": query, "format": "JSON+COLUMNNAME"}).encode("utf-8")
        request = Request(ENDPOINT, data=body, headers={
            "Content-Type": "application/json", "Accept": "application/json",
            "User-Agent": "OutWestSepticSoilLookup/2.0",
        }, method="POST")
        try:
            with urlopen(request, timeout=timeout) as response:
                raw = response.read(MAX_RESPONSE_BYTES + 1)
            if len(raw) > MAX_RESPONSE_BYTES:
                raise SoilDataError("USDA response exceeded the 2 MiB limit.")
            payload = json.loads(raw)
        except (HTTPException, URLError, OSError, UnicodeError, ValueError) as exc:
            raise SoilDataError(
                "USDA request failed or returned invalid JSON; no local data were substituted."
            ) from exc
        return parse_response(payload, mukey)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=(
        "Read USDA SSURGO map-unit components for research. No septic suitability rating."
    ))
    parser.add_argument("--mukey", required=True, help="Map-unit key from USDA Web Soil Survey.")
    parser.add_argument("--json", action="store_true", help="Print a report with provenance as JSON.")
    parser.add_argument("--timeout", type=float, default=20.0, help="Network timeout (0 < seconds <= 60).")
    args = parser.parse_args(argv)
    try:
        report = OutWestSepticSoilLookup.fetch_usda(args.mukey, args.timeout)
    except ValueError as exc:
        print(f"Input error: {exc}", file=sys.stderr)
        return 2
    except SoilDataError as exc:
        print(f"Lookup unavailable: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(asdict(report), indent=2, allow_nan=False) if args.json else report.render())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
