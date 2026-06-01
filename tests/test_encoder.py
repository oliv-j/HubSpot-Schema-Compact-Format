import contextlib
import copy
import io
import json
import tempfile
import unittest
from pathlib import Path

from hscf.cli import main as cli_main
from hscf.encode import encode, expand_property_row, load_json, write_encoded, write_json

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
        self.assertEqual(
            result.full["e"]["example_region"]["ref"],
            "options/synthetic_contact.example_region.hsp-options.json",
        )
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

    def test_known_unmodelled_property_fields_are_preserved(self):
        raw = copy.deepcopy(load_json(FIXTURE))
        prop = raw["result"]["properties"][0]
        prop["createdAt"] = "2026-01-01T00:00:00Z"
        prop["updatedAt"] = "2026-01-02T00:00:00Z"
        prop["createdUserId"] = "12345"
        prop["displayOrder"] = 99

        result = encode(raw, object_key="synthetic_contact")
        idx = result.full["idx"]["prop"]["email"]
        expanded = expand_property_row(result.full, idx)

        self.assertEqual(expanded["x"]["createdAt"], "2026-01-01T00:00:00Z")
        self.assertEqual(expanded["x"]["updatedAt"], "2026-01-02T00:00:00Z")
        self.assertEqual(expanded["x"]["createdUserId"], "12345")
        self.assertEqual(expanded["x"]["displayOrder"], 99)

    def test_known_top_level_user_fields_are_preserved_in_metadata(self):
        raw = copy.deepcopy(load_json(FIXTURE))
        raw["result"]["createdByUserId"] = "111"
        raw["result"]["updatedByUserId"] = "222"

        result = encode(raw, object_key="synthetic_contact")

        self.assertEqual(result.full["m"]["createdByUserId"], "111")
        self.assertEqual(result.full["m"]["updatedByUserId"], "222")

    def test_known_unmodelled_association_fields_are_preserved(self):
        raw = copy.deepcopy(load_json(FIXTURE))
        assoc = raw["result"]["associations"][0]
        assoc["createdAt"] = "2026-01-03T00:00:00Z"
        assoc["updatedAt"] = "2026-01-04T00:00:00Z"

        result = encode(raw, object_key="synthetic_contact")
        ak = result.full["ak"]
        assoc_row = list(result.full["a"][0])
        assoc_row.extend([None] * (len(ak) - len(assoc_row)))
        expanded = dict(zip(ak, assoc_row))

        self.assertEqual(expanded["x"]["createdAt"], "2026-01-03T00:00:00Z")
        self.assertEqual(expanded["x"]["updatedAt"], "2026-01-04T00:00:00Z")

    def test_property_cli_falls_back_to_embedded_rows_for_standalone_full_pack(self):
        raw = load_json(FIXTURE)
        result = encode(raw, object_key="synthetic_contact")

        with tempfile.TemporaryDirectory() as tmp:
            full_path = Path(tmp) / "synthetic_contact.hsp.json"
            write_json(full_path, result.full)

            stdout = io.StringIO()
            with contextlib.redirect_stdout(stdout):
                exit_code = cli_main(["property", str(full_path), "email"])

            self.assertEqual(exit_code, 0)
            expanded = json.loads(stdout.getvalue())
            self.assertEqual(expanded["n"], "email")
            self.assertEqual(expanded["t"], "string")

    def test_enum_sidecar_refs_do_not_collide_after_safe_key_normalization(self):
        raw = {
            "name": "colliding_object",
            "properties": [
                {
                    "name": "foo bar",
                    "label": "Foo Bar",
                    "type": "enumeration",
                    "fieldType": "select",
                    "options": [{"label": "Alpha", "value": "alpha"}],
                },
                {
                    "name": "foo/bar",
                    "label": "Foo Slash Bar",
                    "type": "enumeration",
                    "fieldType": "select",
                    "options": [{"label": "Beta", "value": "beta"}],
                },
            ],
        }

        result = encode(raw, object_key="colliding_object", option_count_threshold=0)

        self.assertEqual(result.full["p"][0][7], "foo bar")
        self.assertEqual(result.full["p"][1][7], "foo/bar")
        self.assertIn("foo bar", result.full["e"])
        self.assertIn("foo/bar", result.full["e"])
        self.assertEqual(
            result.full["e"]["foo bar"]["ref"],
            "options/colliding_object.foo_bar.hsp-options.json",
        )
        self.assertEqual(
            result.full["e"]["foo/bar"]["ref"],
            "options/colliding_object.foo_bar__foo%2Fbar.hsp-options.json",
        )
        self.assertIn("options/colliding_object.foo_bar.hsp-options.json", result.option_sidecars)
        self.assertIn("options/colliding_object.foo_bar__foo%2Fbar.hsp-options.json", result.option_sidecars)
        self.assertEqual(
            result.option_sidecars["options/colliding_object.foo_bar.hsp-options.json"]["property"],
            "foo bar",
        )
        self.assertEqual(
            result.option_sidecars["options/colliding_object.foo_bar__foo%2Fbar.hsp-options.json"]["property"],
            "foo/bar",
        )

    def test_rows_do_not_exceed_property_key_length(self):
        raw = load_json(FIXTURE)
        result = encode(raw, object_key="synthetic_contact")
        pk_len = len(result.full["pk"])
        for row in result.full["p"]:
            self.assertLessEqual(len(row), pk_len)


if __name__ == "__main__":
    unittest.main()
