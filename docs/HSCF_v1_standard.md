# HSCF v1 standard

## 1. Name

**HSCF** stands for **HubSpot schema compact format**.

HSCF v1 is a deterministic, JSON-based format for representing HubSpot object schemas in a way that supports low-token agent retrieval while preserving the source schema data.

The encoded output file is called a **HubSpot schema pack**.

Recommended file extension:

```text
.hsp.json
```

Recommended full-pack filename:

```text
<object-name>.hsp.json
```

Recommended view filename:

```text
<object-name>.hsp-view.json
```

## 2. Purpose

HSCF exists to let agents work with HubSpot object schemas without loading the full HubSpot schema JSON into context.

The practical target is:

1. Agents almost never load the full schema.
2. Agents load a thin view first.
3. Agents use a property index to identify relevant rows.
4. Agents load only selected property rows.
5. Agents open enum sidecars only when enum validation is needed.

HSCF is not a HubSpot product or external standard. It is a proposed open format for compact HubSpot schema representation.

## 3. Design principles

HSCF v1 follows these principles:

1. **Programmatic first**: encoding should be performed by deterministic code, not by agent interpretation.
2. **Lossless canonical pack**: the full profile should preserve enough information to reconstruct the meaningful source schema.
3. **Sparse retrieval by default**: agents should use a view profile and sidecars rather than loading the full pack.
4. **No silent data loss**: unknown fields must be preserved or reported.
5. **Stable output**: the same input schema should produce the same encoded output.
6. **Human inspectable**: the format remains JSON, with compact row maps for interpretation.
7. **Custom-object safe**: the format must work for standard HubSpot objects and portal-specific custom objects.

## 4. Input schema expectations

The input is a HubSpot object schema JSON export.

The encoder must accept either:

1. A direct HubSpot schema object.
2. A wrapper object containing the schema under `result`.

The encoder must support at least these HubSpot schema sections:

```text
labels
requiredProperties
searchableProperties
primaryDisplayProperty
secondaryDisplayProperties
description
allowsSensitiveProperties
archived
restorable
metaType
id
fullyQualifiedName
createdAt
updatedAt
objectTypeId
properties
associations
name
```

`properties` is required.

`associations` is optional because not all schema exports include associations.

## 5. Artefact types

HSCF v1 defines four common artefact types.

### 5.1 Full schema pack

Canonical, mostly lossless representation.

```text
<object-name>.hsp.json
```

Use for:

- validation
- audit
- decoding
- regeneration
- full migration tasks
- unknown-field inspection

### 5.2 View schema pack

Thin agent entrypoint.

```text
<object-name>.hsp-view.json
```

Use for:

- prompt loading
- property discovery
- object metadata inspection
- locating property rows

### 5.3 Property rows sidecar

Optional, recommended for medium and large schemas.

```text
parts/<object-name>.props.hsp.json
```

Use when the view should avoid embedding all property rows.

### 5.4 Enum option sidecars

Recommended by default above the enum sidecar threshold.

```text
options/<object-name>/<property-name>.hsp-options.json
```

Use when an enum option set is large or only needed for validation.

## 6. Profiles

Every HSCF file must declare a profile.

```json
"profile": "full"
```

or:

```json
"profile": "view"
```

### 6.1 Full profile

The full profile is the canonical schema pack.

Required top-level keys:

```text
v
kind
profile
m
pk
p
idx
refs
raw
```

Conditionally required top-level keys:

```text
d    required if property rows use dictionary IDs
ek   required if e is present
e    required if enum option sets are encoded inline or referenced
ak   required if a is present
a    required if associations are encoded inline
wk   required if w is present
w    required if warnings are present
x    required if unknown or non-core fields are preserved
```

Recommended full profile shape:

```json
{
  "v": "hscf-1",
  "kind": "hubspot_schema_pack",
  "profile": "full",
  "m": {},
  "d": {},
  "pk": [],
  "p": [],
  "ek": [],
  "e": {},
  "ak": [],
  "a": [],
  "idx": {"prop": {}},
  "refs": {},
  "x": {},
  "wk": [],
  "w": [],
  "raw": {}
}
```

### 6.2 View profile

The view profile is a low-token access layer for agents.

Required top-level keys:

```text
v
kind
profile
m
pk
idx
refs
raw
```

Recommended view profile shape:

```json
{
  "v": "hscf-1",
  "kind": "hubspot_schema_pack",
  "profile": "view",
  "m": {},
  "pk": [],
  "idx": {"prop": {}},
  "refs": {},
  "raw": {}
}
```

The view profile should normally omit:

```text
p
e
a
x
w
```

unless they are small and useful for the intended retrieval task.

## 7. Metadata block: `m`

The `m` block stores object-level metadata.

Recommended keys:

| Key | Meaning |
|---|---|
| `ot` | HubSpot `objectTypeId` |
| `id` | HubSpot schema `id` |
| `fqn` | `fullyQualifiedName` |
| `name` | object `name`, if present |
| `mt` | `metaType` |
| `labels` | `[singular, plural]` |
| `desc` | object description |
| `req` | required properties |
| `search` | searchable properties |
| `pd` | primary display property |
| `sd` | secondary display properties |
| `sensitive` | `allowsSensitiveProperties` |
| `archived` | object archived state |
| `restorable` | object restorable state |
| `createdAt` | schema created timestamp |
| `updatedAt` | schema updated timestamp |

Example:

```json
{
  "ot": "2-62883809",
  "id": "62883809",
  "fqn": "p51501853_delegates",
  "name": "delegates",
  "mt": "PORTAL_SPECIFIC",
  "labels": ["Delegate", "Delegates"],
  "desc": "Delegates represent a contact's registration and attendance at an event.",
  "req": ["email"],
  "search": ["sw_registrant_id", "event_name", "email"],
  "pd": "email",
  "sd": ["event_name", "sw_registrant_id"]
}
```

## 8. Property rows

Properties are encoded as positional rows.

The property row key array is stored in `pk`.

Recommended `pk` for HSCF v1:

```json
["n", "l", "t", "ft", "g", "desc", "eo", "f", "mm", "hints", "x"]
```

| Key | Meaning |
|---|---|
| `n` | property internal name |
| `l` | label |
| `t` | HubSpot property `type` |
| `ft` | HubSpot `fieldType` |
| `g` | `groupName` |
| `desc` | description |
| `eo` | enum option set reference or null |
| `f` | compact property flags integer |
| `mm` | compact modification metadata flags integer |
| `hints` | date, number, currency, or display hints |
| `x` | preserved extra fields for this property |

Example row using raw strings:

```json
["email", "email", "string", "text", "delegates_information", "", null, 64, 0]
```

Example row using dictionary IDs:

```json
["email", "email", 0, 0, 0, "", null, 64, 0]
```

## 9. Trailing-null omission rule

Property, enum, association, and warning rows may omit trailing `null` values.

Readers must restore omitted trailing cells as `null` up to the length of the relevant key array.

Example with this `pk`:

```json
["n", "l", "t", "ft", "g", "desc", "eo", "f", "mm", "hints", "x"]
```

This row:

```json
["email", "email", "string", "text", "delegates_information", "", null, 64]
```

is equivalent to:

```json
["email", "email", "string", "text", "delegates_information", "", null, 64, null, null, null]
```

Interior nulls must not be omitted.

Invalid:

```json
["email", "email", "string", "text", "delegates_information", "", 64]
```

because the `null` for `eo` has been skipped.

## 10. Dictionary block: `d`

The dictionary block reduces repeated values in full packs.

If present, `d` must be used concretely. Do not include an unused dictionary.

Recommended dictionary keys:

| Key | Encoded values |
|---|---|
| `t` | property `type` values |
| `ft` | property `fieldType` values |
| `g` | property `groupName` values |
| `ds` | `dataSensitivity` values, if modelled in rows or extras |

Example:

```json
{
  "t": ["string", "number", "datetime", "bool", "enumeration"],
  "ft": ["text", "textarea", "number", "date", "select", "checkbox"],
  "g": ["delegates_information"]
}
```

When dictionary encoding is used, row cells for `t`, `ft`, and `g` must contain integer indexes into the corresponding dictionary arrays.

Full profile recommendation:

```text
Use dictionary IDs for t, ft, and g.
```

View profile recommendation:

```text
Dictionary use is optional. Raw strings are acceptable when the view remains small and readability is useful.
```

## 11. Property flags: `f`

Property booleans are compacted into a flags integer.

Recommended bit assignments:

| Bit | Value | Source field |
|---:|---:|---|
| 0 | 1 | `calculated` |
| 1 | 2 | `externalOptions` |
| 2 | 4 | `archived` |
| 3 | 8 | `hasUniqueValue` |
| 4 | 16 | `hidden` |
| 5 | 32 | `hubspotDefined` |
| 6 | 64 | `formField` |
| 7 | 128 | `showCurrencySymbol` |

If a source field is absent, treat it as `false` for flag calculation unless preserved in `x` is required for exact reconstruction.

## 12. Modification metadata flags: `mm`

Recommended bit assignments:

| Bit | Value | Source field |
|---:|---:|---|
| 0 | 1 | `modificationMetadata.archivable` |
| 1 | 2 | `modificationMetadata.readOnlyDefinition` |
| 2 | 4 | `modificationMetadata.readOnlyValue` |
| 3 | 8 | `modificationMetadata.readOnlyOptions` |

If `modificationMetadata` is absent, set `mm` to `null` unless exact absence must be preserved in `x`.

## 13. Hints

The `hints` cell stores optional display and interpretation hints.

Known hint fields include:

```text
dateDisplayHint
numberDisplayHint
showCurrencySymbol
referencedObjectType
```

If no hints are present, use `null` or omit as a trailing null.

Example:

```json
{"numberDisplayHint": "unformatted"}
```

## 14. Enum option sets

Enum option sets are stored in `e` or in enum sidecars.

A property row points to an enum option set using `eo`.

Example property row:

```json
["lc_mediums", "LC Activity", "enumeration", "checkbox", "delegates_information", "", "eo_lc_mediums", 64]
```

### 14.1 Enum key array: `ek`

Recommended enum row key array:

```json
["l", "v", "desc", "o", "h"]
```

| Key | Meaning |
|---|---|
| `l` | option label |
| `v` | option value |
| `desc` | option description |
| `o` | display order |
| `h` | hidden flag, `1` for hidden, `0` for visible |

Example inline option set:

```json
{
  "eo_lc_mediums": [
    ["In Person", "In Person", "", 0, 0],
    ["Online", "Online", "", 1, 0],
    ["On Demand", "On Demand", "", 2, 0],
    ["Masterclass", "Masterclass", "", 3, 0]
  ]
}
```

### 14.2 Enum sidecar threshold

Enum sidecars are the default above either threshold:

```text
option count > 25
encoded option-set size > 4 KB
```

The encoder may use a lower threshold if the target is highly token-constrained.

Example sidecar reference:

```json
{
  "eo_amr_state_name": {
    "ref": "options/contacts/amr_state_name.hsp-options.json",
    "count": 567,
    "hash": "sha256:..."
  }
}
```

### 14.3 Enum sidecar shape

Recommended enum sidecar shape:

```json
{
  "v": "hscf-1",
  "kind": "hubspot_schema_options",
  "profile": "sidecar",
  "property": "amr_state_name",
  "ek": ["l", "v", "desc", "o", "h"],
  "options": []
}
```

## 15. Associations

Associations are encoded as positional rows.

Associations are usually needed only for tasks involving object relationships. They should not be loaded by agents by default.

### 15.1 Association key array: `ak`

Recommended `ak`:

```json
[
  "from",
  "to",
  "name",
  "card",
  "invCard",
  "maxTo",
  "maxFrom",
  "id",
  "umTo",
  "umFrom"
]
```

| Key | Meaning |
|---|---|
| `from` | `fromObjectTypeId` |
| `to` | `toObjectTypeId` |
| `name` | association name |
| `card` | cardinality |
| `invCard` | inverse cardinality |
| `maxTo` | max to-object IDs |
| `maxFrom` | max from-object IDs |
| `id` | association ID |
| `umTo` | `hasUserEnforcedMaxToObjectIds` |
| `umFrom` | `hasUserEnforcedMaxFromObjectIds` |

Example:

```json
[
  "2-62883809",
  "0-1",
  "contact_to_delegates",
  "ONE_TO_MANY",
  "ONE_TO_MANY",
  1,
  500000,
  "132",
  1,
  0
]
```

The full profile should preserve directional association rows.

Agents may reason from simplified derived association views, but those views must not replace the canonical directional rows.

## 16. Indexes

By default, HSCF should include only `idx.prop`.

```json
{
  "idx": {
    "prop": {
      "email": 4,
      "event_name": 8,
      "sw_registrant_id": 72
    }
  }
}
```

`idx.prop` maps property internal names to property row numbers.

Additional indexes are optional and should not be included in the default view unless there is a clear retrieval need.

Optional extra indexes may include:

```text
idxExtra.group
idxExtra.type
idxExtra.assocByName
idxExtra.assocByTarget
```

## 17. References: `refs`

The `refs` block points to related artefacts.

Recommended keys:

| Key | Meaning |
|---|---|
| `full` | path to full schema pack |
| `view` | path to view schema pack |
| `props` | path to property sidecar |
| `optionsDir` | directory containing enum sidecars |
| `associations` | optional association sidecar |

Example view refs:

```json
{
  "full": "delegates.hsp.json",
  "props": "parts/delegates.props.hsp.json",
  "optionsDir": "options/delegates/"
}
```

## 18. Unknown and extra fields: `x`

The encoder must not silently discard unknown fields.

Unknown or non-core fields must be preserved in `x` or produce an error. Known HubSpot fields that are deliberately not modelled as dedicated HSCF fields are still non-core for encoding purposes and must be preserved in `x`.

Recommended structure:

```json
{
  "x": {
    "topLevel": {},
    "objectExtras": {},
    "propertyExtras": {},
    "associationExtras": {}
  }
}
```

Examples of fields that may be stored in `x` if not modelled elsewhere:

```text
createdUserId
updatedUserId
createdByUserId
updatedByUserId
dataSensitivity
unrecognised HubSpot fields
```

If a field affects safe use, such as writeability or value validation, prefer modelling it in core rows rather than hiding it in `x`.

## 19. Warnings

Warnings are stored as compact tuples.

### 19.1 Warning key array: `wk`

Recommended `wk`:

```json
["sev", "code", "path", "msg"]
```

Severity values:

| Value | Meaning |
|---|---|
| `i` | info |
| `w` | warning |
| `e` | error |

Example:

```json
{
  "wk": ["sev", "code", "path", "msg"],
  "w": [
    ["w", "UNKNOWN_PROPERTY_KEY", "$.properties[42].newField", "Preserved in x"],
    ["i", "OPTION_SET_SIDECAR_WRITTEN", "$.properties[12].options", "567 options"]
  ]
}
```

Verbose warning objects may be generated for human reports, but the schema pack should use compact warning tuples.

## 20. Raw source tracking: `raw`

The `raw` block tracks provenance and source integrity.

Recommended keys:

| Key | Meaning |
|---|---|
| `sourceHash` | SHA-256 hash of canonicalised source schema JSON |
| `sourceShape` | source shape, e.g. `hubspot.schemas.get` |
| `encodedAt` | encoding timestamp |
| `encoder` | encoder name/version |

Example:

```json
{
  "sourceHash": "sha256:...",
  "sourceShape": "hubspot.schemas.get",
  "encodedAt": "2026-05-23T00:00:00Z",
  "encoder": "hscf-python/0.1.0"
}
```

## 21. Recommended prompt loading order

Agents should use this loading order by default:

1. Load the view schema pack: `<object-name>.hsp-view.json`.
2. Read `m` first to identify the object, required properties, searchable properties, and display properties.
3. Read `idx.prop` second to find row numbers for relevant property names.
4. Load only selected property rows from `refs.props` or from the full pack.
5. If a selected property has an enum option reference, load the enum sidecar only when validation, mapping, or allowed-value selection is needed.
6. Load association rows only when the task concerns relationships between objects.
7. Load the full schema pack only for audit, migration, decoder work, unknown-field inspection, or when the view and sidecars are insufficient.

Agents should not load the full schema pack by default.

## 22. Encoder algorithm

A conforming HSCF encoder should follow this process.

### 22.1 Read and normalise

1. Parse input JSON.
2. If the object contains `result`, treat `result` as the schema body.
3. Validate that `properties` exists and is an array.
4. Sort or preserve properties deterministically. Recommended: preserve HubSpot order unless a stable sorted mode is explicitly configured.
5. Compute a canonical source hash.

### 22.2 Extract metadata

Map HubSpot object metadata into `m`.

At minimum, extract:

```text
objectTypeId
id
fullyQualifiedName
name
metaType
labels
requiredProperties
searchableProperties
primaryDisplayProperty
secondaryDisplayProperties
description
```

### 22.3 Encode properties

For each property:

1. Create a row according to `pk`.
2. Encode `type`, `fieldType`, and `groupName` using dictionaries in the full profile.
3. Encode property booleans into `f`.
4. Encode `modificationMetadata` into `mm`.
5. Move large enum options into sidecars.
6. Store unmodelled fields in the property row `x` cell or in an equivalent `x.propertyExtras[propertyName]` structure.
7. Apply trailing-null omission.

### 22.4 Encode enum options

For each property with `options`:

1. If options are empty, set `eo` to `null`.
2. If option count is above threshold, create an enum sidecar and put a reference in `e`.
3. Otherwise, encode options inline in `e`.
4. Preserve label, value, description, display order, and hidden state.

### 22.5 Encode associations

If associations exist:

1. Encode directional rows according to `ak`.
2. Preserve user-enforced max flags.
3. Preserve unknown and known-but-unmodelled association fields in the association row `x` cell or in an equivalent `x.associationExtras` structure.
4. Do not deduplicate away directional rows in the full profile.

### 22.6 Build indexes

Build `idx.prop` only by default.

The value must be the zero-based row number in `p` or in the property sidecar.

### 22.7 Build view profile

The view profile should include:

```text
v
kind
profile
m
pk
idx.prop
refs
raw
```

It may include selected rows only if the generated view is still small.

### 22.8 Emit warnings

Emit compact warnings for:

```text
unknown top-level keys
unknown property keys
unknown association keys
missing recommended metadata
large enum sidecar creation
fields preserved in x
unsupported input shape
```

If safe encoding is impossible, emit an error and fail the encode step.

## 23. Decoder requirements

A conforming decoder must be able to:

1. Read `pk`, `ek`, `ak`, and `wk` arrays.
2. Restore omitted trailing nulls.
3. Resolve dictionary IDs.
4. Resolve enum sidecar references.
5. Expand property rows into object form.
6. Expand association rows into object form.
7. Surface warnings in human-readable form.
8. Preserve `x` fields when reconstructing or inspecting the schema.

## 24. Agent behaviour contract

Agents using HSCF should follow these rules:

1. Start from the view profile unless explicitly asked to audit or transform the full schema.
2. Never assume the view profile is complete.
3. Use `idx.prop` to locate properties by internal name.
4. Load property rows before giving property-specific advice.
5. Load enum sidecars before validating or selecting enum values.
6. Check flags before recommending writes.
7. Treat calculated, hidden, HubSpot-defined, read-only, and externally sourced option properties with caution.
8. Load associations only for relationship tasks.
9. Report when information is unavailable because the relevant sidecar or full pack was not loaded.
10. Do not invent schema fields that are not present in the pack.

## 25. Minimal full profile example

```json
{
  "v": "hscf-1",
  "kind": "hubspot_schema_pack",
  "profile": "full",
  "m": {
    "ot": "2-62883809",
    "id": "62883809",
    "fqn": "p51501853_delegates",
    "name": "delegates",
    "mt": "PORTAL_SPECIFIC",
    "labels": ["Delegate", "Delegates"],
    "req": ["email"],
    "search": ["sw_registrant_id", "event_name", "email"],
    "pd": "email",
    "sd": ["event_name", "sw_registrant_id"]
  },
  "d": {
    "t": ["string", "number", "datetime", "bool", "enumeration"],
    "ft": ["text", "textarea", "number", "date", "select", "checkbox"],
    "g": ["delegates_information"]
  },
  "pk": ["n", "l", "t", "ft", "g", "desc", "eo", "f", "mm", "hints", "x"],
  "p": [
    ["email", "email", 0, 0, 0, "", null, 64, 1],
    ["sw_registrant_id", "Registrant ID", 1, 2, 0, "", null, 72, 1, {"numberDisplayHint": "unformatted"}],
    ["lc_mediums", "LC Activity", 4, 5, 0, "", "eo_lc_mediums", 64, 1]
  ],
  "ek": ["l", "v", "desc", "o", "h"],
  "e": {
    "eo_lc_mediums": [
      ["In Person", "In Person", "", 0, 0],
      ["Online", "Online", "", 1, 0],
      ["On Demand", "On Demand", "", 2, 0],
      ["Masterclass", "Masterclass", "", 3, 0]
    ]
  },
  "idx": {
    "prop": {
      "email": 0,
      "sw_registrant_id": 1,
      "lc_mediums": 2
    }
  },
  "refs": {
    "view": "delegates.hsp-view.json",
    "optionsDir": "options/delegates/"
  },
  "raw": {
    "sourceHash": "sha256:...",
    "sourceShape": "hubspot.schemas.get"
  }
}
```

## 26. Minimal view profile example

```json
{
  "v": "hscf-1",
  "kind": "hubspot_schema_pack",
  "profile": "view",
  "m": {
    "ot": "2-62883809",
    "id": "62883809",
    "fqn": "p51501853_delegates",
    "name": "delegates",
    "mt": "PORTAL_SPECIFIC",
    "labels": ["Delegate", "Delegates"],
    "req": ["email"],
    "search": ["sw_registrant_id", "event_name", "email"],
    "pd": "email",
    "sd": ["event_name", "sw_registrant_id"]
  },
  "pk": ["n", "l", "t", "ft", "g", "desc", "eo", "f", "mm", "hints", "x"],
  "idx": {
    "prop": {
      "email": 0,
      "sw_registrant_id": 1,
      "lc_mediums": 2
    }
  },
  "refs": {
    "full": "delegates.hsp.json",
    "props": "parts/delegates.props.hsp.json",
    "optionsDir": "options/delegates/"
  },
  "raw": {
    "sourceHash": "sha256:..."
  }
}
```

## 27. Compliance levels

### 27.1 HSCF-compatible

A file is HSCF-compatible if it:

1. Declares `v: "hscf-1"`.
2. Declares `kind: "hubspot_schema_pack"`.
3. Declares `profile` as `full` or `view`.
4. Includes required top-level keys for its profile.
5. Uses valid row key arrays for positional rows.

### 27.2 HSCF-lossless-full

A full profile is HSCF-lossless-full if it:

1. Preserves all known core fields.
2. Preserves unknown fields in `x`.
3. Preserves enum option details.
4. Preserves association directionality.
5. Stores or references all sidecars needed to inspect the encoded schema.
6. Provides a source hash.

### 27.3 HSCF-agent-view

A view profile is HSCF-agent-view if it:

1. Contains object metadata.
2. Contains `idx.prop`.
3. Points to full pack and property rows via `refs`.
4. Avoids loading full property, enum, and association data by default.

## 28. Non-goals

HSCF v1 does not define:

1. A HubSpot API client.
2. A schema fetch schedule.
3. A database storage model.
4. A semantic property ontology.
5. A replacement for HubSpot source schemas.
6. A guarantee that a view profile is complete.

## 29. Recommended repository structure

```text
hscf/
  README.md
  docs/
    HSCF_v1_standard.md
  schemas/
    hscf-full.schema.json
    hscf-view.schema.json
    hscf-options.schema.json
  scripts/
    encode_hscf.py
    decode_hscf.py
    inspect_hscf.py
  examples/
    source/
      minimal-contact.schema.json
      minimal-custom-object.schema.json
    hscf/
      minimal-contact.hsp.json
      minimal-contact.hsp-view.json
      minimal-custom-object.hsp.json
      minimal-custom-object.hsp-view.json
  tests/
    test_encode.py
    test_decode.py
```

## 30. Required warning for public repos

Do not publish private HubSpot schema exports unless they have been reviewed for sensitivity.

HubSpot schema files may reveal:

```text
internal property names
business processes
integration names
third-party systems
deprecated fields
compliance fields
workflow logic hints
association model details
```

Public HSCF repositories should use synthetic or sanitised examples.
