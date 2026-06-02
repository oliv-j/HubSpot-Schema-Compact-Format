import contextlib
import copy
import io
import json
import re
import tempfile
import unittest
from pathlib import Path

from hscf.cli import main as cli_main
from hscf.encode import encode, expand_property_row, load_json, write_encoded, write_json
from hscf.workflow import encode_workflow, expand_step_row, write_workflow_encoded

OBJECT_FIXTURE = Path(__file__).resolve().parents[1] / "examples" / "objects" / "raw" / "synthetic_contact_schema.json"
WORKFLOW_V4_1798882476 = Path(__file__).resolve().parents[1] / "examples" / "workflows" / "raw" / "1798882476.workflow.json"
WORKFLOW_V4_1616884398 = Path(__file__).resolve().parents[1] / "examples" / "workflows" / "raw" / "1616884398.workflow.json"
WORKFLOW_V4_1743507592 = Path(__file__).resolve().parents[1] / "examples" / "workflows" / "raw" / "1743507592.workflow.json"
WORKFLOW_V4_1698324629 = Path(__file__).resolve().parents[1] / "examples" / "workflows" / "raw" / "1698324629.workflow.json"
WORKFLOW_PACK_SCHEMA = Path(__file__).resolve().parents[1] / "schemas" / "workflows" / "hwcf-pack-v1.schema.json"
WORKFLOW_STEPS_SCHEMA = Path(__file__).resolve().parents[1] / "schemas" / "workflows" / "hwcf-steps-v1.schema.json"
PROD_WORKFLOW_FIXTURES = [
    ("1798882476", WORKFLOW_V4_1798882476),
    ("1616884398", WORKFLOW_V4_1616884398),
    ("1743507592", WORKFLOW_V4_1743507592),
    ("1698324629", WORKFLOW_V4_1698324629),
]
PRIMARY_WORKFLOW_FIXTURE = WORKFLOW_V4_1616884398


def _json_type_matches(expected, value):
    if isinstance(expected, list):
        return any(_json_type_matches(item, value) for item in expected)
    if expected == "object":
        return isinstance(value, dict)
    if expected == "array":
        return isinstance(value, list)
    if expected == "string":
        return isinstance(value, str)
    if expected == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if expected == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if expected == "boolean":
        return isinstance(value, bool)
    if expected == "null":
        return value is None
    return True


def _validate_schema(schema, value, path="$"):
    if "const" in schema:
        assert value == schema["const"], f"{path} expected const {schema['const']!r}, got {value!r}"
    if "enum" in schema:
        assert value in schema["enum"], f"{path} expected one of {schema['enum']!r}, got {value!r}"
    if "type" in schema:
        assert _json_type_matches(schema["type"], value), f"{path} expected type {schema['type']!r}, got {type(value).__name__}"
    if "pattern" in schema and isinstance(value, str):
        assert re.match(schema["pattern"], value), f"{path} did not match pattern"
    if "minimum" in schema and isinstance(value, (int, float)):
        assert value >= schema["minimum"], f"{path} was below minimum"

    if "required" in schema and isinstance(value, dict):
        for key in schema["required"]:
            assert key in value, f"{path} missing required key {key!r}"

    if "properties" in schema and isinstance(value, dict):
        for key, sub_schema in schema["properties"].items():
            if key in value:
                _validate_schema(sub_schema, value[key], f"{path}.{key}")

    if "items" in schema and isinstance(value, list):
        item_schema = schema["items"]
        for idx, item in enumerate(value):
            _validate_schema(item_schema, item, f"{path}[{idx}]")

    if "additionalProperties" in schema and isinstance(value, dict):
        additional = schema["additionalProperties"]
        allowed = set(schema.get("properties", {}).keys())
        if additional is False:
            for key in value:
                assert key in allowed, f"{path} had unexpected key {key!r}"
        elif isinstance(additional, dict):
            for key, item in value.items():
                if key not in allowed:
                    _validate_schema(additional, item, f"{path}.{key}")

    if "not" in schema:
        try:
            _validate_schema(schema["not"], value, path)
        except AssertionError:
            pass
        else:
            raise AssertionError(f"{path} matched forbidden schema")

    for branch in schema.get("allOf", []):
        _validate_schema(branch, value, path)

    if "if" in schema:
        try:
            _validate_schema(schema["if"], value, path)
        except AssertionError:
            pass
        else:
            if "then" in schema:
                _validate_schema(schema["then"], value, path)


class EncoderTests(unittest.TestCase):
    def test_encode_profiles_and_sidecar(self):
        raw = load_json(OBJECT_FIXTURE)
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
        raw = load_json(OBJECT_FIXTURE)
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
        raw = load_json(OBJECT_FIXTURE)
        result = encode(raw, object_key="synthetic_contact")
        warnings = [w[1] for w in result.full["w"]]
        self.assertIn("UNKNOWN_PROPERTY_KEY", warnings)

        idx = result.full["idx"]["prop"]["example_region"]
        expanded = expand_property_row(result.full, idx)
        self.assertIn("futureHubSpotKey", expanded["x"])

    def test_known_unmodelled_property_fields_are_preserved(self):
        raw = copy.deepcopy(load_json(OBJECT_FIXTURE))
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
        raw = copy.deepcopy(load_json(OBJECT_FIXTURE))
        raw["result"]["createdByUserId"] = "111"
        raw["result"]["updatedByUserId"] = "222"

        result = encode(raw, object_key="synthetic_contact")

        self.assertEqual(result.full["m"]["createdByUserId"], "111")
        self.assertEqual(result.full["m"]["updatedByUserId"], "222")

    def test_known_unmodelled_association_fields_are_preserved(self):
        raw = copy.deepcopy(load_json(OBJECT_FIXTURE))
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
        raw = load_json(OBJECT_FIXTURE)
        result = encode(raw, object_key="synthetic_contact")

        with tempfile.TemporaryDirectory() as tmp:
            full_path = Path(tmp) / "synthetic_contact.hsp.json"
            write_json(full_path, result.full)

            stdout = io.StringIO()
            with contextlib.redirect_stdout(stdout):
                exit_code = cli_main(["objects", "property", str(full_path), "email"])

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
        raw = load_json(OBJECT_FIXTURE)
        result = encode(raw, object_key="synthetic_contact")
        pk_len = len(result.full["pk"])
        for row in result.full["p"]:
            self.assertLessEqual(len(row), pk_len)

    def test_workflow_encode_profiles_and_step_index(self):
        raw = load_json(PRIMARY_WORKFLOW_FIXTURE)
        result = encode_workflow(raw, workflow_key="1616884398")

        self.assertEqual(result.full["profile"], "full")
        self.assertEqual(result.view["profile"], "view")
        self.assertIn("idx", result.view)
        self.assertEqual(set(result.view["idx"].keys()), {"step", "type"})
        self.assertIn("30", result.full["idx"]["step"])
        self.assertIn("SINGLE_CONNECTION", result.full["idx"]["type"])

    def test_workflow_write_and_expand_step(self):
        raw = load_json(PRIMARY_WORKFLOW_FIXTURE)
        result = encode_workflow(raw, workflow_key="1616884398")

        with tempfile.TemporaryDirectory() as tmp:
            written = write_workflow_encoded(result, tmp, "1616884398")
            self.assertTrue(Path(written["full"]).exists())
            self.assertTrue(Path(written["view"]).exists())
            self.assertTrue(Path(written["steps"]).exists())

            steps = load_json(written["steps"])
            row_index = result.view["idx"]["step"]["30"]
            expanded = expand_step_row(steps, row_index)
            self.assertEqual(expanded["id"], "30")
            self.assertEqual(expanded["t"], "SINGLE_CONNECTION")
            self.assertEqual(expanded["asset"]["contentId"], "186579717408")
            self.assertEqual(expanded["next"], ["34"])

    def test_workflow_unknown_keys_are_preserved(self):
        raw = {
            "id": "wf-unknowns",
            "name": "Unknowns workflow",
            "type": "CONTACT_BASED",
            "isEnabled": True,
            "futureTopLevelWorkflowKey": "preserve me too",
            "actions": [
                {
                    "actionId": "rotate_1",
                    "type": "rotateOwner",
                    "futureWorkflowField": "preserve me",
                }
            ],
        }
        result = encode_workflow(raw, workflow_key="wf_unknowns")
        warnings = [w[1] for w in result.full["w"]]
        self.assertIn("UNKNOWN_WORKFLOW_KEY", warnings)
        self.assertIn("UNKNOWN_ACTION_KEY", warnings)

        idx = result.full["idx"]["step"]["rotate_1"]
        expanded = expand_step_row(result.full, idx)
        self.assertEqual(expanded["x"]["futureWorkflowField"], "preserve me")
        self.assertEqual(result.full["x"]["top"]["futureTopLevelWorkflowKey"], "preserve me too")

    def test_workflow_step_cli_falls_back_to_embedded_rows_for_standalone_full_pack(self):
        raw = load_json(PRIMARY_WORKFLOW_FIXTURE)
        result = encode_workflow(raw, workflow_key="1616884398")

        with tempfile.TemporaryDirectory() as tmp:
            full_path = Path(tmp) / "1616884398.hwp.json"
            write_json(full_path, result.full)

            stdout = io.StringIO()
            with contextlib.redirect_stdout(stdout):
                exit_code = cli_main(["workflows", "step", str(full_path), "30"])

            self.assertEqual(exit_code, 0)
            expanded = json.loads(stdout.getvalue())
            self.assertEqual(expanded["id"], "30")
            self.assertEqual(expanded["t"], "SINGLE_CONNECTION")

    def test_workflow_metadata_and_retrieval_summaries(self):
        raw = load_json(WORKFLOW_V4_1798882476)
        result = encode_workflow(raw, workflow_key="1798882476")

        metadata = result.view["m"]
        self.assertEqual(metadata["stepCount"], len(result.view["idx"]["step"]))
        self.assertEqual(metadata["excludedActionCount"], 0)
        self.assertEqual(metadata["goalCount"], 0)
        self.assertTrue(metadata["hasEnrollmentCriteria"])
        self.assertFalse(metadata["hasUnenrollmentCriteria"])
        self.assertEqual(metadata["suppressionListCount"], 0)
        self.assertEqual(result.full["x"]["summary"]["enrollment"]["type"], "EVENT_BASED")
        self.assertEqual(result.full["x"]["summary"]["enrollment"]["eventBranchCount"], 2)
        self.assertEqual(result.full["x"]["summary"]["blockedDates"]["count"], len(raw["blockedDates"]))

    def test_workflow_branch_and_timing_are_modeled(self):
        raw = load_json(PRIMARY_WORKFLOW_FIXTURE)
        result = encode_workflow(raw, workflow_key="1616884398")

        branch_step = expand_step_row(result.full, result.full["idx"]["step"]["31"])
        self.assertEqual(branch_step["branch"]["kind"], "STATIC_BRANCH")
        self.assertEqual(branch_step["branch"]["count"], 1)
        self.assertEqual(branch_step["hints"]["branchKind"], "STATIC_BRANCH")

        delay_step = expand_step_row(result.full, result.full["idx"]["step"]["34"])
        self.assertEqual(delay_step["timing"]["kind"], "delay")
        self.assertEqual(delay_step["timing"]["delta"], "10080")
        self.assertEqual(delay_step["hints"]["timingKind"], "delay")

    def test_workflow_direct_actions_shape_is_supported(self):
        raw = {
            "id": "wf-actions",
            "name": "Actions workflow",
            "type": "CONTACT_BASED",
            "isEnabled": False,
            "actions": [
                {"actionId": "a1", "name": "Start", "type": "trigger", "connection": {"nextActionId": "a2"}},
                {"actionId": "a2", "name": "Task", "type": "createTask", "fields": {"taskType": "EMAIL"}},
            ],
        }

        result = encode_workflow(raw, workflow_key="actions_workflow")

        self.assertEqual(result.view["m"]["stepCount"], 2)
        self.assertEqual(result.view["m"]["excludedActionCount"], 0)
        self.assertIn("createTask", result.view["idx"]["type"])
        codes = [warning[1] for warning in result.full["w"]]
        self.assertNotIn("ACTION_MISSING_ID", codes)
        self.assertIn("a1", result.view["idx"]["step"])
        self.assertFalse(result.view["m"]["enabled"])

    def test_workflow_wrapped_actions_shape_is_supported(self):
        raw = {
            "ok": True,
            "source": "hubspot",
            "result": {
                "id": "wf-wrapped",
                "name": "Wrapped workflow",
                "type": "CONTACT_BASED",
                "isEnabled": True,
                "actions": [
                    {"actionId": "wrapped", "type": "sendEmail", "fields": {"content_id": "123"}}
                ],
            },
        }

        result = encode_workflow(raw, workflow_key="wrapped")

        self.assertEqual(list(result.full["idx"]["step"].keys()), ["wrapped"])
        self.assertEqual(result.view["m"]["excludedActionCount"], 0)
        self.assertEqual(result.full["x"]["sourceMeta"]["source"], "hubspot")

    def test_workflow_missing_action_id_is_not_indexed(self):
        raw = {
            "id": "wf-missing-id",
            "name": "Missing id",
            "type": "CONTACT_BASED",
            "actions": [
                {"id": "legacy-only", "name": "Legacy only", "type": "delay"},
                {"actionId": "good", "name": "Good", "type": "delay"},
            ],
        }

        result = encode_workflow(raw, workflow_key="missing_id")

        self.assertEqual(list(result.full["idx"]["step"].keys()), ["good"])
        self.assertEqual(len(result.full["s"]), 1)
        self.assertIn("ACTION_MISSING_ID", [warning[1] for warning in result.full["w"]])
        self.assertIn("INDEXED_ACTION_COUNT_MISMATCH", [warning[1] for warning in result.full["w"]])
        self.assertEqual(result.view["m"]["stepCount"], 1)
        self.assertEqual(result.view["m"]["excludedActionCount"], 1)
        self.assertEqual(result.full["x"]["summary"]["exclusions"]["count"], 1)

    def test_workflow_duplicate_action_id_excludes_later_rows(self):
        raw = {
            "id": "wf-dup",
            "name": "Duplicate id",
            "type": "CONTACT_BASED",
            "actions": [
                {"actionId": "dup", "name": "First", "type": "sendEmail"},
                {"actionId": "dup", "name": "Second", "type": "delay"},
            ],
        }

        result = encode_workflow(raw, workflow_key="dup")

        self.assertEqual(result.view["m"]["stepCount"], 1)
        self.assertEqual(result.view["m"]["excludedActionCount"], 1)
        self.assertEqual(result.full["idx"]["step"]["dup"], 0)
        self.assertEqual(len(result.full["s"]), 1)
        self.assertEqual(len(result.steps_part["s"]), 1)
        self.assertEqual(result.full["idx"]["type"]["sendEmail"], ["dup"])
        self.assertNotIn("delay", result.full["idx"]["type"])
        warnings = [warning[1] for warning in result.full["w"]]
        self.assertIn("DUPLICATE_ACTION_ID", warnings)
        self.assertIn("INDEXED_ACTION_COUNT_MISMATCH", warnings)

        first = expand_step_row(result.full, result.full["idx"]["step"]["dup"])
        self.assertEqual(first["n"], "First")
        self.assertEqual(result.full["x"]["summary"]["exclusions"]["count"], 1)

    def test_workflow_view_signals_partial_encode(self):
        raw = {
            "id": "wf-partial",
            "name": "Partial",
            "type": "CONTACT_BASED",
            "actions": [
                {"actionId": "good", "type": "sendEmail"},
                {"id": "legacy-only", "type": "delay"},
            ],
        }

        result = encode_workflow(raw, workflow_key="partial")

        self.assertEqual(result.view["m"]["stepCount"], 1)
        self.assertEqual(result.view["m"]["excludedActionCount"], 1)
        self.assertEqual(len(result.full["s"]), 1)

    def test_workflow_steps_input_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "containing actions"):
            encode_workflow({"id": "wf-steps", "steps": [{"id": "legacy"}]}, workflow_key="legacy")

    def test_workflow_rows_do_not_exceed_step_key_length(self):
        raw = load_json(PRIMARY_WORKFLOW_FIXTURE)
        result = encode_workflow(raw, workflow_key="1616884398")
        sk_len = len(result.full["sk"])
        for row in result.full["s"]:
            self.assertLessEqual(len(row), sk_len)

    def test_workflow_pack_and_steps_part_match_schemas(self):
        raw = load_json(PRIMARY_WORKFLOW_FIXTURE)
        result = encode_workflow(raw, workflow_key="1616884398")
        pack_schema = load_json(WORKFLOW_PACK_SCHEMA)
        steps_schema = load_json(WORKFLOW_STEPS_SCHEMA)

        _validate_schema(pack_schema, result.full)
        _validate_schema(pack_schema, result.view)
        _validate_schema(steps_schema, result.steps_part)

    def test_prod_workflows_encode_with_indexed_actions(self):
        baselines = {
            "1798882476": {"actions": 16, "unknown_max": 2},
            "1616884398": {"actions": 49, "unknown_max": 4},
            "1743507592": {"actions": 2, "unknown_max": 2},
            "1698324629": {"actions": 6, "unknown_max": 2},
        }

        for workflow_id, fixture in PROD_WORKFLOW_FIXTURES:
            with self.subTest(workflow_id=workflow_id):
                raw = load_json(fixture)
                result = encode_workflow(raw, workflow_key=workflow_id)
                actions = raw.get("actions", [])
                self.assertEqual(len(result.full["s"]), len(actions))
                self.assertEqual(len(result.full["idx"]["step"]), len(actions))
                self.assertEqual(result.view["m"]["excludedActionCount"], 0)
                self.assertNotIn("ACTION_MISSING_ID", [warning[1] for warning in result.full["w"]])
                self.assertNotIn("DUPLICATE_ACTION_ID", [warning[1] for warning in result.full["w"]])
                self.assertNotIn("INDEXED_ACTION_COUNT_MISMATCH", [warning[1] for warning in result.full["w"]])
                unknown_count = sum(1 for warning in result.full["w"] if warning[1] == "UNKNOWN_WORKFLOW_KEY")
                self.assertLessEqual(unknown_count, baselines[workflow_id]["unknown_max"])

    def test_prod_workflow_action_rows_are_retrievable(self):
        raw = load_json(WORKFLOW_V4_1616884398)
        result = encode_workflow(raw, workflow_key="1616884398")

        self.assertIn("30", result.view["idx"]["step"])
        self.assertIn("SINGLE_CONNECTION", result.view["idx"]["type"])

        email_action = expand_step_row(result.full, result.view["idx"]["step"]["30"])
        self.assertEqual(email_action["id"], "30")
        self.assertEqual(email_action["asset"]["contentId"], "186579717408")
        self.assertEqual(email_action["next"], ["34"])

    def test_prod_workflow_branch_and_wait_summaries(self):
        raw = load_json(WORKFLOW_V4_1616884398)
        result = encode_workflow(raw, workflow_key="1616884398")

        wait_action = expand_step_row(result.full, result.view["idx"]["step"]["34"])
        self.assertEqual(wait_action["timing"]["delta"], "10080")
        self.assertEqual(wait_action["timing"]["unit"], "MINUTES")
        self.assertTrue(wait_action["hints"]["isWait"])

        branch_action = expand_step_row(result.full, result.view["idx"]["step"]["31"])
        self.assertEqual(branch_action["branch"]["kind"], "STATIC_BRANCH")
        self.assertEqual(branch_action["branch"]["targets"], ["30"])
        self.assertTrue(branch_action["hints"]["isBranch"])

    def test_prod_workflow_custom_code_is_summarized(self):
        raw = load_json(WORKFLOW_V4_1698324629)
        result = encode_workflow(raw, workflow_key="1698324629")

        action = expand_step_row(result.full, result.view["idx"]["step"]["1"])
        self.assertEqual(action["asset"]["runtime"], "PYTHON39")
        self.assertEqual(action["asset"]["secretCount"], 1)
        self.assertTrue(action["hints"]["runsCode"])
        self.assertIn("sourceCode", action["x"])

    def test_prod_workflow_metadata_promotes_v4_fields(self):
        raw = load_json(WORKFLOW_V4_1798882476)
        result = encode_workflow(raw, workflow_key="1798882476")

        metadata = result.view["m"]
        self.assertEqual(metadata["flowType"], "WORKFLOW")
        self.assertEqual(metadata["objectTypeId"], "2-52622293")
        self.assertEqual(metadata["startActionId"], "9")
        self.assertEqual(metadata["nextAvailableActionId"], "17")
        self.assertEqual(metadata["crmObjectCreationStatus"], "COMPLETE")

    def test_prod_workflow_schema_validation(self):
        pack_schema = load_json(WORKFLOW_PACK_SCHEMA)
        steps_schema = load_json(WORKFLOW_STEPS_SCHEMA)

        for workflow_id, fixture in PROD_WORKFLOW_FIXTURES:
            with self.subTest(workflow_id=workflow_id):
                raw = load_json(fixture)
                result = encode_workflow(raw, workflow_key=workflow_id)
                _validate_schema(pack_schema, result.full)
                _validate_schema(pack_schema, result.view)
                _validate_schema(steps_schema, result.steps_part)

    def test_cli_help_separates_objects_and_workflows(self):
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            exit_code = cli_main([])

        self.assertEqual(exit_code, 1)
        help_text = stdout.getvalue()
        self.assertIn("objects", help_text)
        self.assertIn("workflows", help_text)


if __name__ == "__main__":
    unittest.main()
