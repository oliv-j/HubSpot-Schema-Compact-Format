from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

HSCF_VERSION = "hscf-1"
KIND_PACK = "hubspot_schema_pack"
KIND_PROPS = "hscf_property_rows"
KIND_OPTIONS = "hscf_option_set"

PROPERTY_KEYS = ["n", "l", "t", "ft", "g", "desc", "ds", "eo", "f", "mm", "hints", "x"]
OPTION_KEYS = ["l", "v", "d", "o", "h", "x"]
ASSOCIATION_KEYS = ["from", "to", "name", "card", "inv", "maxTo", "maxFrom", "id", "f", "x"]
WARNING_KEYS = ["sev", "code", "path", "msg"]

PROPERTY_FLAG_BITS = {
    "calculated": 1,
    "externalOptions": 2,
    "archived": 4,
    "hasUniqueValue": 8,
    "hidden": 16,
    "hubspotDefined": 32,
    "formField": 64,
    "showCurrencySymbol": 128,
}

ASSOCIATION_FLAG_BITS = {
    "hasUserEnforcedMaxToObjectIds": 1,
    "hasUserEnforcedMaxFromObjectIds": 2,
}

KNOWN_TOP_LEVEL_KEYS = {
    "labels",
    "requiredProperties",
    "searchableProperties",
    "primaryDisplayProperty",
    "secondaryDisplayProperties",
    "description",
    "allowsSensitiveProperties",
    "archived",
    "restorable",
    "metaType",
    "id",
    "fullyQualifiedName",
    "createdAt",
    "updatedAt",
    "createdByUserId",
    "updatedByUserId",
    "objectTypeId",
    "properties",
    "associations",
    "name",
}

KNOWN_PROPERTY_KEYS = {
    "updatedAt",
    "createdAt",
    "name",
    "label",
    "type",
    "fieldType",
    "description",
    "groupName",
    "options",
    "createdUserId",
    "displayOrder",
    "calculated",
    "externalOptions",
    "archived",
    "hasUniqueValue",
    "hidden",
    "hubspotDefined",
    "modificationMetadata",
    "formField",
    "dataSensitivity",
    "showCurrencySymbol",
    "numberDisplayHint",
    "dateDisplayHint",
    "referencedObjectType",
}

KNOWN_OPTION_KEYS = {"label", "value", "description", "displayOrder", "hidden"}

KNOWN_ASSOCIATION_KEYS = {
    "fromObjectTypeId",
    "toObjectTypeId",
    "name",
    "cardinality",
    "inverseCardinality",
    "hasUserEnforcedMaxToObjectIds",
    "hasUserEnforcedMaxFromObjectIds",
    "maxToObjectIds",
    "maxFromObjectIds",
    "id",
    "createdAt",
    "updatedAt",
}

# Keys modelled directly in the compact property row. Known source keys that are
# not listed here must still be preserved in the row's x cell.
ENCODED_PROPERTY_KEYS = {
    "name",
    "label",
    "type",
    "fieldType",
    "description",
    "groupName",
    "options",
    "calculated",
    "externalOptions",
    "archived",
    "hasUniqueValue",
    "hidden",
    "hubspotDefined",
    "modificationMetadata",
    "formField",
    "dataSensitivity",
    "showCurrencySymbol",
    "numberDisplayHint",
    "dateDisplayHint",
    "referencedObjectType",
}

# Keys modelled directly in the compact association row. Known source keys that
# are not listed here must still be preserved in the row's x cell.
ENCODED_ASSOCIATION_KEYS = {
    "fromObjectTypeId",
    "toObjectTypeId",
    "name",
    "cardinality",
    "inverseCardinality",
    "hasUserEnforcedMaxToObjectIds",
    "hasUserEnforcedMaxFromObjectIds",
    "maxToObjectIds",
    "maxFromObjectIds",
    "id",
}


@dataclass
class EncodeResult:
    full: dict[str, Any]
    view: dict[str, Any]
    props_part: dict[str, Any]
    option_sidecars: dict[str, dict[str, Any]] = field(default_factory=dict)


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def sha256_json(value: Any) -> str:
    return "sha256:" + hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def safe_key(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_.-]+", "_", value.strip())
    cleaned = cleaned.strip("._-")
    return cleaned or "schema"


def load_json(path: str | Path) -> Any:
    with Path(path).open("r", encoding="utf-8") as f:
        return json.load(f)


def write_json(path: str | Path, value: Any) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("w", encoding="utf-8") as f:
        json.dump(value, f, ensure_ascii=False, separators=(",", ":"))
        f.write("\n")


def extract_schema(raw: Any) -> tuple[dict[str, Any], dict[str, Any]]:
    """Return (schema, source_meta). Accepts raw schema or wrapped result."""
    if isinstance(raw, dict) and isinstance(raw.get("result"), dict) and "properties" in raw["result"]:
        meta = {k: raw.get(k) for k in ("ok", "source", "portal", "command", "object") if k in raw}
        return raw["result"], meta
    if isinstance(raw, dict) and "properties" in raw:
        return raw, {}
    raise ValueError("Input must be a HubSpot schema object or a wrapper containing result.properties")


def dict_id(dictionary: list[Any], value: Any) -> int | None:
    if value is None:
        return None
    try:
        return dictionary.index(value)
    except ValueError:
        dictionary.append(value)
        return len(dictionary) - 1


def trim_trailing_nulls(row: list[Any]) -> list[Any]:
    while row and row[-1] is None:
        row.pop()
    return row


def flags_from(source: dict[str, Any], bit_map: dict[str, int]) -> int | None:
    flags = 0
    for key, bit in bit_map.items():
        if source.get(key) is True:
            flags |= bit
    return flags or None


def compact_modification_metadata(prop: dict[str, Any]) -> list[Any] | None:
    mm = prop.get("modificationMetadata")
    if not isinstance(mm, dict):
        return None
    row = [
        mm.get("archivable"),
        mm.get("readOnlyDefinition"),
        mm.get("readOnlyValue"),
        mm.get("readOnlyOptions"),
    ]
    return trim_trailing_nulls(row) or None


def compact_hints(prop: dict[str, Any]) -> dict[str, Any] | None:
    hints: dict[str, Any] = {}
    for key in ("numberDisplayHint", "dateDisplayHint", "referencedObjectType"):
        if key in prop:
            hints[key] = prop[key]
    return hints or None


def extras(source: dict[str, Any], known: set[str]) -> dict[str, Any] | None:
    x = {k: v for k, v in source.items() if k not in known}
    return x or None


def option_rows(options: list[dict[str, Any]], warnings: list[list[str]], prop_path: str) -> list[list[Any]]:
    rows: list[list[Any]] = []
    for i, opt in enumerate(options):
        if not isinstance(opt, dict):
            warnings.append(["e", "INVALID_OPTION_SHAPE", f"{prop_path}.options[{i}]", "Option is not an object"])
            continue
        opt_x = extras(opt, KNOWN_OPTION_KEYS)
        if opt_x:
            warnings.append(["w", "UNKNOWN_OPTION_KEY", f"{prop_path}.options[{i}]", "Preserved in option x"])
        row = [
            opt.get("label"),
            opt.get("value"),
            opt.get("description"),
            opt.get("displayOrder"),
            opt.get("hidden"),
            opt_x,
        ]
        rows.append(trim_trailing_nulls(row))
    return rows


def should_sidecar(options_payload: dict[str, Any], count_threshold: int, bytes_threshold: int) -> bool:
    count = len(options_payload.get("o", []))
    size = len(canonical_json(options_payload).encode("utf-8"))
    return count > count_threshold or size > bytes_threshold


def build_metadata(schema: dict[str, Any]) -> dict[str, Any]:
    labels = schema.get("labels") or {}
    return {
        "ot": schema.get("objectTypeId"),
        "id": schema.get("id"),
        "fqn": schema.get("fullyQualifiedName"),
        "name": schema.get("name"),
        "mt": schema.get("metaType"),
        "labels": [labels.get("singular"), labels.get("plural")],
        "desc": schema.get("description"),
        "req": schema.get("requiredProperties") or [],
        "search": schema.get("searchableProperties") or [],
        "pd": schema.get("primaryDisplayProperty"),
        "sd": schema.get("secondaryDisplayProperties") or [],
        "sensitive": schema.get("allowsSensitiveProperties"),
        "archived": schema.get("archived"),
        "restorable": schema.get("restorable"),
        "createdAt": schema.get("createdAt"),
        "updatedAt": schema.get("updatedAt"),
        "createdByUserId": schema.get("createdByUserId"),
        "updatedByUserId": schema.get("updatedByUserId"),
    }


def encode_associations(schema: dict[str, Any], warnings: list[list[str]]) -> list[list[Any]]:
    rows: list[list[Any]] = []
    associations = schema.get("associations") or []
    for i, assoc in enumerate(associations):
        if not isinstance(assoc, dict):
            warnings.append(["e", "INVALID_ASSOCIATION_SHAPE", f"$.associations[{i}]", "Association is not an object"])
            continue
        unknown_assoc_x = extras(assoc, KNOWN_ASSOCIATION_KEYS)
        if unknown_assoc_x:
            warnings.append(["w", "UNKNOWN_ASSOCIATION_KEY", f"$.associations[{i}]", "Preserved in association x"])
        assoc_x = extras(assoc, ENCODED_ASSOCIATION_KEYS)
        row = [
            assoc.get("fromObjectTypeId"),
            assoc.get("toObjectTypeId"),
            assoc.get("name"),
            assoc.get("cardinality"),
            assoc.get("inverseCardinality"),
            assoc.get("maxToObjectIds"),
            assoc.get("maxFromObjectIds"),
            assoc.get("id"),
            flags_from(assoc, ASSOCIATION_FLAG_BITS),
            assoc_x,
        ]
        rows.append(trim_trailing_nulls(row))
    return rows


def encode(raw: Any, *, object_key: str | None = None, option_count_threshold: int = 25, option_bytes_threshold: int = 4096) -> EncodeResult:
    schema, source_meta = extract_schema(raw)
    warnings: list[list[str]] = []

    top_x = extras(schema, KNOWN_TOP_LEVEL_KEYS)
    if top_x:
        for key in top_x:
            warnings.append(["w", "UNKNOWN_TOP_LEVEL_KEY", f"$.{key}", "Preserved in x.top"])

    obj_key = safe_key(object_key or schema.get("fullyQualifiedName") or schema.get("name") or schema.get("objectTypeId") or "schema")

    dictionaries: dict[str, list[Any]] = {"t": [], "ft": [], "g": [], "ds": []}
    e: dict[str, Any] = {}
    option_sidecars: dict[str, dict[str, Any]] = {}
    property_rows: list[list[Any]] = []
    idx_prop: dict[str, int] = {}

    properties = schema.get("properties") or []
    for i, prop in enumerate(properties):
        path = f"$.properties[{i}]"
        if not isinstance(prop, dict):
            warnings.append(["e", "INVALID_PROPERTY_SHAPE", path, "Property is not an object"])
            continue

        name = prop.get("name")
        if not name:
            warnings.append(["e", "PROPERTY_MISSING_NAME", path, "Property not indexed"])
            continue

        unknown_prop_x = extras(prop, KNOWN_PROPERTY_KEYS)
        if unknown_prop_x:
            warnings.append(["w", "UNKNOWN_PROPERTY_KEY", path, "Preserved in property x"])
        prop_x = extras(prop, ENCODED_PROPERTY_KEYS)

        options = prop.get("options") or []
        enum_ref = None
        if options:
            enum_ref = safe_key(str(name))
            opt_payload = {
                "v": HSCF_VERSION,
                "kind": KIND_OPTIONS,
                "object": obj_key,
                "property": name,
                "ek": OPTION_KEYS,
                "o": option_rows(options, warnings, path),
                "raw": {"sourceHash": sha256_json(options)},
            }
            if should_sidecar(opt_payload, option_count_threshold, option_bytes_threshold):
                ref = f"options/{obj_key}.{safe_key(str(name))}.hsp-options.json"
                e[enum_ref] = {"ref": ref, "count": len(options), "hash": opt_payload["raw"]["sourceHash"]}
                option_sidecars[ref] = opt_payload
                warnings.append(["i", "OPTION_SET_SIDECAR_WRITTEN", f"{path}.options", f"{len(options)} options"])
            else:
                e[enum_ref] = opt_payload

        row = [
            name,
            prop.get("label"),
            dict_id(dictionaries["t"], prop.get("type")),
            dict_id(dictionaries["ft"], prop.get("fieldType")),
            dict_id(dictionaries["g"], prop.get("groupName")),
            prop.get("description"),
            dict_id(dictionaries["ds"], prop.get("dataSensitivity")),
            enum_ref,
            flags_from(prop, PROPERTY_FLAG_BITS),
            compact_modification_metadata(prop),
            compact_hints(prop),
            prop_x,
        ]
        idx_prop[str(name)] = len(property_rows)
        property_rows.append(trim_trailing_nulls(row))

    associations = encode_associations(schema, warnings)
    metadata = build_metadata(schema)
    raw_hash = sha256_json(raw)

    refs = {
        "view": f"{obj_key}.hsp-view.json",
        "props": f"parts/{obj_key}.hsp-props.json",
        "optionsDir": "options/",
    }

    full = {
        "v": HSCF_VERSION,
        "kind": KIND_PACK,
        "profile": "full",
        "m": metadata,
        "d": dictionaries,
        "pk": PROPERTY_KEYS,
        "p": property_rows,
        "ek": OPTION_KEYS,
        "e": e,
        "ak": ASSOCIATION_KEYS,
        "a": associations,
        "idx": {"prop": idx_prop},
        "refs": refs,
        "x": {"top": top_x, "sourceMeta": source_meta} if top_x or source_meta else {},
        "wk": WARNING_KEYS,
        "w": warnings,
        "raw": {"sourceHash": raw_hash, "encodedAt": utc_now()},
    }

    props_part = {
        "v": HSCF_VERSION,
        "kind": KIND_PROPS,
        "profile": "part",
        "object": obj_key,
        "d": dictionaries,
        "pk": PROPERTY_KEYS,
        "p": property_rows,
        "raw": {"sourceHash": raw_hash},
    }

    view = {
        "v": HSCF_VERSION,
        "kind": KIND_PACK,
        "profile": "view",
        "m": metadata,
        "pk": PROPERTY_KEYS,
        "idx": {"prop": idx_prop},
        "refs": {
            "full": f"{obj_key}.hsp.json",
            "props": f"parts/{obj_key}.hsp-props.json",
            "optionsDir": "options/",
        },
        "raw": {"sourceHash": raw_hash},
    }

    return EncodeResult(full=full, view=view, props_part=props_part, option_sidecars=option_sidecars)


def write_encoded(result: EncodeResult, output_dir: str | Path, object_key: str) -> dict[str, str]:
    out = Path(output_dir)
    obj_key = safe_key(object_key)
    written: dict[str, str] = {}

    full_path = out / f"{obj_key}.hsp.json"
    view_path = out / f"{obj_key}.hsp-view.json"
    props_path = out / "parts" / f"{obj_key}.hsp-props.json"

    write_json(full_path, result.full)
    write_json(view_path, result.view)
    write_json(props_path, result.props_part)

    written["full"] = str(full_path)
    written["view"] = str(view_path)
    written["props"] = str(props_path)

    for rel, payload in result.option_sidecars.items():
        sidecar_path = out / rel
        write_json(sidecar_path, payload)
        written[rel] = str(sidecar_path)

    return written


def expand_property_row(pack_or_part: dict[str, Any], row_index: int) -> dict[str, Any]:
    pk = pack_or_part["pk"]
    row = list(pack_or_part["p"][row_index])
    row.extend([None] * (len(pk) - len(row)))
    expanded = dict(zip(pk, row))

    d = pack_or_part.get("d", {})
    for key in ("t", "ft", "g", "ds"):
        value = expanded.get(key)
        if isinstance(value, int) and key in d and value < len(d[key]):
            expanded[key] = d[key][value]
    return expanded
