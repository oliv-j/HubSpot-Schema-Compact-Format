# HSCF implementation notes

This document describes the bare minimum implementation pattern.

## Input

The encoder accepts either of these shapes:

```json
{
  "properties": []
}
```

or:

```json
{
  "ok": true,
  "source": "hubspot",
  "portal": "example",
  "command": "schemas.get",
  "object": "contacts",
  "result": {
    "properties": []
  }
}
```

The second shape is common when schema exports are wrapped with extraction metadata.

## Output

For object key `contacts`, emit:

```text
contacts.hsp.json
contacts.hsp-view.json
parts/contacts.hsp-props.json
options/*.hsp-options.json
```

## Full profile

The full profile is the canonical compact representation.

Required keys:

```text
v, kind, profile, m, d, pk, p, ek, e, ak, a, idx, refs, x, wk, w, raw
```

## View profile

The view profile is the low-token entrypoint for agents.

Required keys:

```text
v, kind, profile, m, pk, idx, refs, raw
```

A view file should keep only `idx.prop` by default.

## Dictionary encoding

In the full profile, encode repeated property values as dictionary integers:

```text
t  = property type
ft = HubSpot field type
g  = HubSpot group name
ds = data sensitivity
```

Example:

```json
"d": {
  "t": ["string", "number", "enumeration"],
  "ft": ["text", "number", "select"],
  "g": ["contactinformation"],
  "ds": ["non_sensitive"]
}
```

## Property rows

Default `pk`:

```json
["n", "l", "t", "ft", "g", "desc", "ds", "eo", "f", "mm", "hints", "x"]
```

Rows may omit trailing nulls. Readers must restore missing trailing cells as nulls up to the length of `pk`.

Interior nulls must not be omitted.

## Flags

Property flag bitset `f`:

```text
1   calculated
2   externalOptions
4   archived
8   hasUniqueValue
16  hidden
32  hubspotDefined
64  formField
128 showCurrencySymbol
```

Association flag bitset:

```text
1 hasUserEnforcedMaxToObjectIds
2 hasUserEnforcedMaxFromObjectIds
```

## Enum sidecars

Default sidecar threshold:

```text
option count > 25 OR encoded option-set size > 4096 bytes
```

Small option sets may be inline in `e`. Larger option sets should be written to `options/` and referenced from `e`.

## Warnings

Use compact warning tuples.

```json
"wk": ["sev", "code", "path", "msg"],
"w": [
  ["w", "UNKNOWN_PROPERTY_KEY", "$.properties[0].newKey", "Preserved in x"]
]
```

## Preservation

Unknown fields and known-but-unmodelled source fields must be preserved under `x` where practical. Unknown data should not be discarded silently. For example, if `displayOrder`, property `createdAt`, property `updatedAt`, property `createdUserId`, or association timestamps are not modelled as dedicated columns, preserve them in the relevant row `x` cell.

## Hashing

Compute a source hash from canonical JSON:

```text
json.dumps(raw, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
```

Store it as:

```json
"raw": {
  "sourceHash": "sha256:..."
}
```
