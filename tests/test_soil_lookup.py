"""Offline boundary and failure tests. Fixture values are synthetic."""
import contextlib
import io
from http.client import IncompleteRead
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import MagicMock, patch
from urllib.error import URLError

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import outwestseptic_soil_lookup as soil


def fixture():
    return {"Table": [list(soil.COLUMNS),
        ["TX363", "Example survey", "2026-01-01", "123", "X", "Example map unit",
         "456", "Example component", "80", "Well drained"],
        ["TX363", "Example survey", "2026-01-01", "123", "X", "Example map unit",
         "457", "Minor component", None, None],
    ]}


class ParsingTests(unittest.TestCase):
    def test_preserves_missing_values_and_provenance(self):
        report = soil.parse_response(fixture(), "123")
        self.assertEqual(report.components[0].representative_percent, 80)
        self.assertIsNone(report.components[1].representative_percent)
        self.assertIsNone(report.components[1].drainage_class)
        self.assertEqual(report.source, soil.ENDPOINT)
        self.assertEqual(report.survey_version_date, "2026-01-01")
        self.assertIn("not reported", report.render())
        self.assertIn("No percolation rate", report.render())
        self.assertNotIn("septic_suitability", soil.asdict(report))

    def test_reordered_columns(self):
        data = fixture()
        data["Table"] = [list(reversed(row)) for row in data["Table"]]
        self.assertEqual(soil.parse_response(data, "123").mukey, "123")

    def test_map_unit_without_components(self):
        data = fixture()
        data["Table"] = data["Table"][:2]
        data["Table"][1][6:] = [None] * 4
        report = soil.parse_response(data, "123")
        self.assertEqual(report.components, ())
        self.assertIn("No component records", report.render())

    def test_invalid_responses_fail_closed(self):
        for payload in (None, [], {}, {"Table": []}, {"Table": [list(soil.COLUMNS)]},
                        {"Table": ["bad", []]}, {"Table": [list(soil.COLUMNS), []]}):
            with self.subTest(payload=payload), self.assertRaises(soil.SoilDataError):
                soil.parse_response(payload, "123")

    def test_wrong_map_unit_or_mixed_metadata(self):
        for col, value in ((3, "999"), (0, "TX999"), (5, "Different unit")):
            data = fixture()
            data["Table"][2][col] = value
            with self.subTest(col=col), self.assertRaises(soil.SoilDataError):
                soil.parse_response(data, "123")

    def test_missing_or_duplicate_component_key(self):
        for value in (None, "456"):
            data = fixture()
            data["Table"][2][6] = value
            with self.subTest(value=value), self.assertRaises(soil.SoilDataError):
                soil.parse_response(data, "123")

    def test_percent_boundaries(self):
        for value in (0, "0", 100, "100", None, ""):
            data = fixture()
            data["Table"][1][8] = value
            soil.parse_response(data, "123")
        for value in (-1, "101", "nan", "inf", 1.5, True, {}, "-2"):
            data = fixture()
            data["Table"][1][8] = value
            with self.subTest(value=value), self.assertRaises(soil.SoilDataError):
                soil.parse_response(data, "123")

    def test_does_not_normalize_component_totals(self):
        data = fixture()
        data["Table"][2][8] = "30"
        report = soil.parse_response(data, "123")
        self.assertEqual([c.representative_percent for c in report.components], [80, 30])


class ClientTests(unittest.TestCase):
    def test_rejects_keys_without_network(self):
        for key in ("", "0", "-1", "1.2", "１２３", "123; DROP TABLE mapunit", " 123", 123, True):
            with self.subTest(key=key), patch.object(soil, "urlopen") as opener:
                with self.assertRaises(ValueError):
                    soil.OutWestSepticSoilLookup.fetch_usda(key)
                opener.assert_not_called()

    def test_rejects_bad_timeout_without_network(self):
        for timeout in (0, -1, float("inf"), float("nan"), True, "20", 61):
            with self.subTest(timeout=timeout), patch.object(soil, "urlopen") as opener:
                with self.assertRaises(ValueError):
                    soil.OutWestSepticSoilLookup.fetch_usda("123", timeout)
                opener.assert_not_called()

    def test_official_post_request_and_response(self):
        response = MagicMock()
        response.__enter__.return_value.read.return_value = json.dumps(fixture()).encode()
        with patch.object(soil, "urlopen", return_value=response) as opener:
            report = soil.OutWestSepticSoilLookup.fetch_usda("123")
        request = opener.call_args.args[0]
        self.assertEqual(request.full_url, soil.ENDPOINT)
        self.assertEqual(request.get_method(), "POST")
        body = json.loads(request.data)
        self.assertEqual(body["format"], "JSON+COLUMNNAME")
        self.assertIn("m.mukey = '123'", body["query"])
        self.assertIn("Non-MLRA Soil Survey Area", body["query"])
        self.assertEqual(report.mukey, "123")

    def test_network_failures_do_not_fall_back(self):
        for error in (URLError("unavailable"), TimeoutError("timeout"), IncompleteRead(b"partial", 200)):
            with self.subTest(error=error), patch.object(soil, "urlopen", side_effect=error):
                with self.assertRaises(soil.SoilDataError):
                    soil.OutWestSepticSoilLookup.fetch_usda("123")

    def test_truncated_http_body_returns_clean_error(self):
        response = MagicMock()
        response.__enter__.return_value.read.side_effect = IncompleteRead(b"partial", 200)
        with patch.object(soil, "urlopen", return_value=response), contextlib.redirect_stderr(io.StringIO()) as error:
            self.assertEqual(soil.main(["--mukey", "123"]), 1)
        self.assertNotIn("Traceback", error.getvalue())

    def test_invalid_and_oversized_response(self):
        for raw in (b"<html>service unavailable</html>", b"x" * (soil.MAX_RESPONSE_BYTES + 1)):
            response = MagicMock()
            response.__enter__.return_value.read.return_value = raw
            with patch.object(soil, "urlopen", return_value=response):
                with self.assertRaises(soil.SoilDataError):
                    soil.OutWestSepticSoilLookup.fetch_usda("123")

    def test_cli_json_success_and_exit_codes(self):
        with patch.object(soil.OutWestSepticSoilLookup, "fetch_usda", return_value=soil.parse_response(fixture(), "123")), contextlib.redirect_stdout(io.StringIO()) as output:
            self.assertEqual(soil.main(["--mukey", "123", "--json"]), 0)
            self.assertEqual(json.loads(output.getvalue())["mukey"], "123")
        for error, code in ((ValueError("invalid input"), 2), (soil.SoilDataError("no data"), 1)):
            with patch.object(soil.OutWestSepticSoilLookup, "fetch_usda", side_effect=error), contextlib.redirect_stderr(io.StringIO()) as stderr, contextlib.redirect_stdout(io.StringIO()) as stdout:
                self.assertEqual(soil.main(["--mukey", "123"]), code)
                self.assertEqual(stdout.getvalue(), "")
                self.assertNotIn("Traceback", stderr.getvalue())

    def test_legacy_cli_fails_instead_of_returning_presets(self):
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as error:
            soil.main(["Cisco"])
        self.assertEqual(error.exception.code, 2)


if __name__ == "__main__":
    unittest.main()
