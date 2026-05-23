import json
import tempfile
import unittest
from pathlib import Path

from hscf.encode import encode, expand_property_row, load_json, write_encoded

FIXTURE = Path(__file__).resolve().parents[1] / "examples" / "raw" / "synthetic_contact_schema.json"


class EncoderTests(unittest.TestCase):
    def test_encode_profiles_and_sidecar(self):
        raw = load_json(FIXTURE)
        result = encode(raw, object_key="synthetic_contact", option_count_threshold=25)

        self.assertEqual(result.full["profile"], "full")
        self.assertEqual(result.view["profile"], "view")
        self.assertIn("idx", result.view)
        self.assertEqual(set(result.view["idx"].keys()), {"prop"})
        self.assertIn("example_region", result.full["e"])
        self.assertIn("ref", result.full["e"]["example_region"])
        self.assertTrue(result.option_sidecars)

    def test_write_and_expand_property(self):
        raw = load_json(FIXTURE)
        result = encode(raw, object_key="synthetic_contact")
        with tempfile.TemporaryDirectory() as tmp:
            written = write_encoded(result, tmp, "synthetic_contact")
            self.assertTrue(Path(written["full"]).exists())
            self.assertTrue(Path(written["view"]).exists())
            self.assertTrue(Path(written["props"]).exists())

            props = load_json(written["props"])
            row_index = result.view["idx"]["prop"]["email"]
            expanded = expand_property_row(props, row_index)
            self.assertEqual(expanded["n"], "email")
            self.assertEqual(expanded["t"], "string")
            self.assertEqual(expanded["ft"], "text")

    def test_unknown_property_key_warning_and_preservation(self):
        raw = load_json(FIXTURE)
        result = encode(raw, object_key="synthetic_contact")
        warnings = [w[1] for w in result.full["w"]]
        self.assertIn("UNKNOWN_PROPERTY_KEY", warnings)

        idx = result.full["idx"]["prop"]["example_region"]
        expanded = expand_property_row(result.full, idx)
        self.assertIn("futureHubSpotKey", expanded["x"])

    def test_rows_do_not_exceed_property_key_length(self):
        raw = load_json(FIXTURE)
        result = encode(raw, object_key="synthetic_contact")
        pk_len = len(result.full["pk"])
        for row in result.full["p"]:
            self.assertLessEqual(len(row), pk_len)


if __name__ == "__main__":
    unittest.main()
