from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .encode import dict_id, extras, safe_key, sha256_json, trim_trailing_nulls, utc_now, write_json

HWCF_VERSION = "hwcf-1"
KIND_WORKFLOW_PACK = "hubspot_workflow_pack"
KIND_WORKFLOW_STEPS = "hwcf_step_rows"
WARNING_KEYS = ["sev", "code", "path", "msg"]
ACTION_KEYS = ["id", "n", "t", "next", "branch", "timing", "asset", "goal", "f", "hints", "x"]
STEP_FLAG_BITS = {
    "isBranch": 1,
    "hasDelay": 2,
    "hasAsset": 4,
    "hasCode": 8,
    "terminal": 16,
    "updatesProperty": 32,
}
KNOWN_TOP_LEVEL_KEYS = {
    "id",
    "name",
    "type",
    "description",
    "createdAt",
    "updatedAt",
    "revisionId",
    "actions",
    "flowType",
    "isEnabled",
    "objectTypeId",
    "uuid",
    "startActionId",
    "nextAvailableActionId",
    "crmObjectCreationStatus",
    "enrollmentCriteria",
    "timeWindows",
    "blockedDates",
    "customProperties",
    "dataSources",
    "goals",
    "folderId",
    "settings",
    "canEnrollFromSalesforce",
    "suppressionListIds",
    "suppressionLists",
    "unenrollmentCriteria",
}
KNOWN_ACTION_KEYS = {
    "id",
    "actionId",
    "name",
    "type",
    "connection",
    "staticBranches",
    "defaultBranch",
    "defaultBranchName",
    "listBranches",
    "testBranches",
    "fields",
    "inputValue",
    "inputFields",
    "outputFields",
    "runtime",
    "secretNames",
    "sourceCode",
    "actionTypeId",
    "actionTypeVersion",
}
ENCODED_ACTION_KEYS = {
    "id",
    "actionId",
    "name",
    "type",
    "connection",
    "staticBranches",
    "defaultBranch",
    "defaultBranchName",
    "listBranches",
    "testBranches",
    "fields",
    "inputValue",
    "inputFields",
    "outputFields",
    "runtime",
    "secretNames",
    "sourceCode",
}


@dataclass
class WorkflowEncodeResult:
    full: dict[str, Any]
    view: dict[str, Any]
    steps_part: dict[str, Any]
    sidecars: dict[str, dict[str, Any]] = field(default_factory=dict)


def extract_workflow(raw: Any) -> tuple[dict[str, Any], dict[str, Any]]:
    if isinstance(raw, dict) and isinstance(raw.get("result"), dict):
        result = raw["result"]
        if "actions" in result:
            meta = {k: raw.get(k) for k in ("ok", "source", "portal", "command", "workflow") if k in raw}
            return result, meta
    if isinstance(raw, dict) and "actions" in raw:
        return raw, {}
    raise ValueError("Input must be a workflow object or wrapper containing actions")


def _normalized_action_id(action: dict[str, Any]) -> str | None:
    action_id = action.get("actionId")
    if action_id is not None and str(action_id).strip():
        return str(action_id).strip()
    return None


def _coerce_action_type(action: dict[str, Any]) -> str | None:
    action_type = action.get("type")
    if action_type is not None:
        return str(action_type)
    action_type_id = action.get("actionTypeId")
    if action_type_id is not None:
        return f"ACTION_TYPE_{action_type_id}"
    return None


def _extract_next_ids(action: dict[str, Any], warnings: list[list[str]], path: str) -> list[str]:
    next_ids: list[str] = []

    def add_target(value: Any) -> None:
        if value is None:
            return
        text = str(value).strip()
        if text:
            next_ids.append(text)

    connection = action.get("connection")
    if isinstance(connection, dict):
        add_target(connection.get("nextActionId"))
    elif connection is not None:
        warnings.append(["w", "MALFORMED_CONNECTION", f"{path}.connection", "Preserved in action x"])

    for branch_key in ("staticBranches", "listBranches", "testBranches"):
        branch_list = action.get(branch_key)
        if branch_list is None:
            continue
        if not isinstance(branch_list, list):
            warnings.append(["w", "MALFORMED_BRANCH_LIST", f"{path}.{branch_key}", "Preserved in action x"])
            continue
        for index, branch in enumerate(branch_list):
            if not isinstance(branch, dict):
                warnings.append(["w", "MALFORMED_BRANCH_NODE", f"{path}.{branch_key}[{index}]", "Preserved in action x"])
                continue
            target = branch.get("connection")
            if isinstance(target, dict):
                add_target(target.get("nextActionId"))
            elif target is not None:
                warnings.append(["w", "MALFORMED_CONNECTION", f"{path}.{branch_key}[{index}].connection", "Preserved in action x"])

    default_branch = action.get("defaultBranch")
    if isinstance(default_branch, dict):
        add_target(default_branch.get("nextActionId"))
    elif default_branch is not None:
        warnings.append(["w", "MALFORMED_CONNECTION", f"{path}.defaultBranch", "Preserved in action x"])

    deduped: list[str] = []
    seen: set[str] = set()
    for item in next_ids:
        if item not in seen:
            deduped.append(item)
            seen.add(item)
    return deduped


def _branch_summary(action: dict[str, Any], next_ids: list[str], warnings: list[list[str]], path: str) -> dict[str, Any] | None:
    branch_kind = None
    branches: list[Any] = []
    labels: list[str] = []

    if isinstance(action.get("staticBranches"), list):
        branch_kind = "STATIC_BRANCH"
        branches = action["staticBranches"]
        for branch in branches:
            if isinstance(branch, dict) and branch.get("branchValue") is not None:
                labels.append(str(branch.get("branchValue")))
    elif isinstance(action.get("listBranches"), list):
        branch_kind = "LIST_BRANCH"
        branches = action["listBranches"]
        for branch in branches:
            if isinstance(branch, dict) and branch.get("branchName") is not None:
                labels.append(str(branch.get("branchName")))
    elif isinstance(action.get("testBranches"), list):
        branch_kind = "AB_TEST_BRANCH"
        branches = action["testBranches"]

    default_branch = action.get("defaultBranch")
    if branch_kind is None and default_branch is None:
        return None

    summary = {
        "kind": branch_kind or "DEFAULT_BRANCH",
        "count": len(branches),
        "hasDefault": isinstance(default_branch, dict),
        "targets": next_ids,
    }
    if labels:
        summary["labels"] = labels
    if isinstance(action.get("defaultBranchName"), str) and action["defaultBranchName"].strip():
        summary["defaultLabel"] = action["defaultBranchName"].strip()
    if not next_ids:
        warnings.append(["w", "BRANCH_WITHOUT_TARGETS", path, "Branch action has no reachable targets"])
    return summary


def _timing_summary(action: dict[str, Any]) -> dict[str, Any] | None:
    fields = action.get("fields")
    if not isinstance(fields, dict):
        return None
    if "delta" not in fields and "time_unit" not in fields and "days_of_week" not in fields:
        return None
    summary: dict[str, Any] = {"kind": "delay"}
    if "delta" in fields:
        summary["delta"] = fields.get("delta")
    if "time_unit" in fields:
        summary["unit"] = fields.get("time_unit")
    if isinstance(fields.get("days_of_week"), list):
        summary["days"] = fields.get("days_of_week")
    return summary


def _asset_summary(action: dict[str, Any]) -> dict[str, Any] | None:
    asset: dict[str, Any] = {}
    fields = action.get("fields")
    if isinstance(fields, dict):
        if "content_id" in fields:
            asset["contentId"] = fields.get("content_id")
        if "emailTemplate" in fields:
            asset["emailTemplate"] = fields.get("emailTemplate")
        if "taskType" in fields:
            asset["taskType"] = fields.get("taskType")
        if "flow_id" in fields:
            asset["flowId"] = fields.get("flow_id")
        if "property_name" in fields:
            asset["propertyName"] = fields.get("property_name")
    if action.get("runtime") is not None:
        asset["runtime"] = action.get("runtime")
    if isinstance(action.get("secretNames"), list) and action["secretNames"]:
        asset["secretCount"] = len(action["secretNames"])
    if isinstance(action.get("inputFields"), list):
        asset["inputFieldCount"] = len(action["inputFields"])
    if isinstance(action.get("outputFields"), list):
        asset["outputFieldCount"] = len(action["outputFields"])
    return asset or None


def _goal_summary(action: dict[str, Any]) -> dict[str, Any] | None:
    input_value = action.get("inputValue")
    if not isinstance(input_value, dict):
        return None
    summary: dict[str, Any] = {}
    if "propertyName" in input_value:
        summary["propertyName"] = input_value.get("propertyName")
    if "type" in input_value:
        summary["type"] = input_value.get("type")
    if "actionId" in input_value:
        summary["sourceActionId"] = input_value.get("actionId")
    if "dataKey" in input_value:
        summary["dataKey"] = input_value.get("dataKey")
    return summary or None


def _action_flags(action: dict[str, Any], next_ids: list[str], branch: dict[str, Any] | None, timing: dict[str, Any] | None, asset: dict[str, Any] | None) -> int | None:
    flags = 0
    if branch is not None:
        flags |= STEP_FLAG_BITS["isBranch"]
    if timing is not None:
        flags |= STEP_FLAG_BITS["hasDelay"]
    if asset is not None:
        flags |= STEP_FLAG_BITS["hasAsset"]
    if action.get("runtime") is not None or action.get("sourceCode") is not None:
        flags |= STEP_FLAG_BITS["hasCode"]
    if isinstance(action.get("fields"), dict) and "property_name" in action["fields"]:
        flags |= STEP_FLAG_BITS["updatesProperty"]
    if not next_ids:
        flags |= STEP_FLAG_BITS["terminal"]
    return flags or None


def _action_hints(action: dict[str, Any], action_type: str | None, branch: dict[str, Any] | None, timing: dict[str, Any] | None, asset: dict[str, Any] | None) -> dict[str, Any] | None:
    hints: dict[str, Any] = {}
    if action_type is not None:
        hints["actionType"] = action_type
    if branch is not None:
        hints["isBranch"] = True
        hints["branchKind"] = branch.get("kind")
    if timing is not None:
        hints["isWait"] = True
        hints["timingKind"] = timing.get("kind")
    if asset is not None and "contentId" in asset:
        hints["sendsEmail"] = True
    if asset is not None and "flowId" in asset:
        hints["triggersWorkflow"] = True
    if asset is not None and "propertyName" in asset:
        hints["updatesProperty"] = True
    if action.get("runtime") is not None or action.get("sourceCode") is not None:
        hints["runsCode"] = True
    if isinstance(action.get("inputFields"), list):
        hints["inputFieldCount"] = len(action["inputFields"])
    if isinstance(action.get("outputFields"), list):
        hints["outputFieldCount"] = len(action["outputFields"])
    return hints or None


def _summarize_predicates(value: Any) -> dict[str, Any] | None:
    if isinstance(value, list):
        return {"count": len(value)}
    if isinstance(value, dict):
        out: dict[str, Any] = {}
        if "type" in value:
            out["type"] = value.get("type")
        if "filters" in value and isinstance(value["filters"], list):
            out["count"] = len(value["filters"])
        if "eventFilterBranches" in value and isinstance(value["eventFilterBranches"], list):
            out["eventBranchCount"] = len(value["eventFilterBranches"])
        if "listMembershipFilterBranches" in value and isinstance(value["listMembershipFilterBranches"], list):
            out["listBranchCount"] = len(value["listMembershipFilterBranches"])
        return out or {"present": True}
    if value is not None:
        return {"present": True}
    return None


def _workflow_metadata(workflow: dict[str, Any], indexed_action_count: int, excluded_action_count: int) -> dict[str, Any]:
    goals = workflow.get("goals")
    suppression_lists = workflow.get("suppressionLists")
    suppression_list_ids = workflow.get("suppressionListIds")
    return {
        "id": workflow.get("id"),
        "name": workflow.get("name"),
        "type": workflow.get("type"),
        "flowType": workflow.get("flowType"),
        "enabled": workflow.get("isEnabled"),
        "desc": workflow.get("description"),
        "createdAt": workflow.get("createdAt"),
        "updatedAt": workflow.get("updatedAt"),
        "revisionId": workflow.get("revisionId"),
        "uuid": workflow.get("uuid"),
        "objectTypeId": workflow.get("objectTypeId"),
        "startActionId": workflow.get("startActionId"),
        "nextAvailableActionId": workflow.get("nextAvailableActionId"),
        "crmObjectCreationStatus": workflow.get("crmObjectCreationStatus"),
        "canEnrollFromSalesforce": workflow.get("canEnrollFromSalesforce"),
        "stepCount": indexed_action_count,
        "goalCount": len(goals) if isinstance(goals, list) else 0,
        "hasEnrollmentCriteria": workflow.get("enrollmentCriteria") is not None,
        "hasUnenrollmentCriteria": workflow.get("unenrollmentCriteria") is not None,
        "suppressionListCount": len(suppression_lists) if isinstance(suppression_lists, list) else len(suppression_list_ids) if isinstance(suppression_list_ids, list) else 0,
        "excludedActionCount": excluded_action_count,
    }


def _workflow_summary(workflow: dict[str, Any], excluded_action_count: int) -> dict[str, Any]:
    summary: dict[str, Any] = {}
    enrollment = _summarize_predicates(workflow.get("enrollmentCriteria"))
    if enrollment:
        summary["enrollment"] = enrollment
    unenrollment = _summarize_predicates(workflow.get("unenrollmentCriteria"))
    if unenrollment:
        summary["unenrollment"] = unenrollment
    goals = workflow.get("goals")
    if isinstance(goals, list):
        summary["goals"] = {"count": len(goals)}
    if isinstance(workflow.get("timeWindows"), list):
        summary["timeWindows"] = {"count": len(workflow["timeWindows"])}
    if isinstance(workflow.get("blockedDates"), list):
        summary["blockedDates"] = {"count": len(workflow["blockedDates"])}
    if isinstance(workflow.get("dataSources"), list):
        summary["dataSources"] = {"count": len(workflow["dataSources"])}
    if isinstance(workflow.get("customProperties"), dict):
        summary["customProperties"] = {"count": len(workflow["customProperties"])}
    if excluded_action_count:
        summary["exclusions"] = {"count": excluded_action_count}
    return summary


def encode_actions(actions: list[Any], warnings: list[list[str]]) -> tuple[list[list[Any]], dict[str, int], dict[str, list[str]], dict[str, list[Any]], int]:
    dictionaries: dict[str, list[Any]] = {"t": []}
    rows: list[list[Any]] = []
    idx_step: dict[str, int] = {}
    idx_type: dict[str, list[str]] = {}
    excluded_count = 0

    for i, action in enumerate(actions):
        path = f"$.actions[{i}]"
        if not isinstance(action, dict):
            warnings.append(["e", "INVALID_ACTION_SHAPE", path, "Action is not an object"])
            excluded_count += 1
            continue

        action_id = _normalized_action_id(action)
        if not action_id:
            warnings.append(["e", "ACTION_MISSING_ID", path, "Action missing required actionId and was excluded"])
            excluded_count += 1
            continue

        action_unknown_x = extras(action, KNOWN_ACTION_KEYS)
        if action_unknown_x:
            for key in action_unknown_x:
                warnings.append(["w", "UNKNOWN_ACTION_KEY", f"{path}.{key}", "Preserved in action x"])

        action_type = _coerce_action_type(action)
        next_ids = _extract_next_ids(action, warnings, path)
        branch = _branch_summary(action, next_ids, warnings, path)
        timing = _timing_summary(action)
        asset = _asset_summary(action)
        goal = _goal_summary(action)
        flags = _action_flags(action, next_ids, branch, timing, asset)
        hints = _action_hints(action, action_type, branch, timing, asset)
        action_x = extras(action, ENCODED_ACTION_KEYS)
        if action.get("sourceCode") is not None:
            action_x = dict(action_x or {})
            action_x["sourceCode"] = action.get("sourceCode")

        row = [
            action_id,
            action.get("name"),
            dict_id(dictionaries["t"], action_type),
            next_ids,
            branch,
            timing,
            asset,
            goal,
            flags,
            hints,
            action_x,
        ]

        if action_id in idx_step:
            warnings.append(["e", "DUPLICATE_ACTION_ID", f"{path}.actionId", f"Duplicate action ID {action_id!r} was excluded"])
            excluded_count += 1
            continue

        idx_step[action_id] = len(rows)
        if action_type is not None:
            idx_type.setdefault(action_type, []).append(action_id)
        rows.append(trim_trailing_nulls(row))

    return rows, idx_step, idx_type, dictionaries, excluded_count


def encode_workflow(raw: Any, *, workflow_key: str | None = None) -> WorkflowEncodeResult:
    workflow, source_meta = extract_workflow(raw)
    warnings: list[list[str]] = []
    actions = list(workflow.get("actions") or [])

    top_x = extras(workflow, KNOWN_TOP_LEVEL_KEYS)
    if top_x:
        for key in top_x:
            warnings.append(["w", "UNKNOWN_WORKFLOW_KEY", f"$.{key}", "Preserved in x.top"])

    wf_key = safe_key(workflow_key or workflow.get("name") or workflow.get("id") or "workflow")
    rows, idx_step, idx_type, dictionaries, excluded_count = encode_actions(actions, warnings)
    metadata = _workflow_metadata(workflow, len(idx_step), excluded_count)
    summary = _workflow_summary(workflow, excluded_count)
    raw_hash = sha256_json(raw)

    if excluded_count:
        warnings.append(
            [
                "w",
                "INDEXED_ACTION_COUNT_MISMATCH",
                "$.actions",
                f"Excluded {excluded_count} of {len(actions)} actions; emitted {len(rows)} indexed rows",
            ]
        )

    refs = {
        "full": f"{wf_key}.hwp.json",
        "steps": f"parts/{wf_key}.hwp-steps.json",
    }

    full = {
        "v": HWCF_VERSION,
        "kind": KIND_WORKFLOW_PACK,
        "profile": "full",
        "m": metadata,
        "d": dictionaries,
        "sk": ACTION_KEYS,
        "s": rows,
        "idx": {"step": idx_step, "type": idx_type},
        "refs": refs,
        "x": {"top": top_x, "sourceMeta": source_meta, "summary": summary} if top_x or source_meta or summary else {},
        "wk": WARNING_KEYS,
        "w": warnings,
        "raw": {"sourceHash": raw_hash, "encodedAt": utc_now()},
    }

    steps_part = {
        "v": HWCF_VERSION,
        "kind": KIND_WORKFLOW_STEPS,
        "profile": "part",
        "workflow": wf_key,
        "d": dictionaries,
        "sk": ACTION_KEYS,
        "s": rows,
        "raw": {"sourceHash": raw_hash},
    }

    view = {
        "v": HWCF_VERSION,
        "kind": KIND_WORKFLOW_PACK,
        "profile": "view",
        "m": metadata,
        "sk": ACTION_KEYS,
        "idx": {"step": idx_step, "type": idx_type},
        "refs": refs,
        "raw": {"sourceHash": raw_hash},
    }

    return WorkflowEncodeResult(full=full, view=view, steps_part=steps_part)


def write_workflow_encoded(result: WorkflowEncodeResult, output_dir: str | Path, workflow_key: str) -> dict[str, str]:
    out = Path(output_dir)
    key = safe_key(workflow_key)
    written: dict[str, str] = {}

    full_path = out / f"{key}.hwp.json"
    view_path = out / f"{key}.hwp-view.json"
    steps_path = out / "parts" / f"{key}.hwp-steps.json"

    write_json(full_path, result.full)
    write_json(view_path, result.view)
    write_json(steps_path, result.steps_part)

    written["full"] = str(full_path)
    written["view"] = str(view_path)
    written["steps"] = str(steps_path)
    return written


def expand_step_row(pack_or_part: dict[str, Any], row_index: int) -> dict[str, Any]:
    sk = pack_or_part["sk"]
    row = list(pack_or_part["s"][row_index])
    row.extend([None] * (len(sk) - len(row)))
    expanded = dict(zip(sk, row))

    d = pack_or_part.get("d", {})
    value = expanded.get("t")
    if isinstance(value, int) and "t" in d and value < len(d["t"]):
        expanded["t"] = d["t"][value]
    return expanded
