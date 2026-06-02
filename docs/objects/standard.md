# HSCF object schema pack format

HSCF is the **HubSpot schema compact format** for HubSpot object schema exports.

## Purpose

HSCF lets agents work with HubSpot object schemas without loading the full export into context.

The normal operating model is:

1. Load the object view file.
2. Read metadata and the property index.
3. Retrieve only the relevant property rows.
4. Open enum sidecars only when needed.
5. Open the full pack only for audit, regeneration, or unknown-field inspection.

## Common artefacts

```text
<object>.hsp.json
<object>.hsp-view.json
parts/<object>.hsp-props.json
options/<object>.<property>.hsp-options.json
```

## Input expectations

The encoder accepts either a direct object schema with `properties` or a wrapped export with `result.properties`.

## Profiles

### Full profile

Canonical compact representation for validation, audit, decoding, and regeneration.

Expected top-level keys:

```text
v, kind, profile, m, d, pk, p, idx, refs, raw
```

It may also include:

```text
ek, e, ak, a, x, wk, w
```

### View profile

Low-token agent entrypoint.

Expected top-level keys:

```text
v, kind, profile, m, pk, idx, refs, raw
```

The view profile should normally omit `p`, `e`, `a`, `x`, and `w`.

## Preservation rules

- Unknown top-level, property, option, and association fields must be preserved under `x`.
- Unknown fields should also produce compact warnings in `w`.
- Known-but-unmodelled fields should be preserved under `x` without being silently dropped.
