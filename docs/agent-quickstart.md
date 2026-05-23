# Agent quickstart

## When asked to implement HSCF

1. Read `docs/HSCF_v1_standard.md`.
2. Locate HubSpot schema exports.
3. Add or update `config/hscf.yml`.
4. Generate HSCF outputs for latest schema files.
5. Offer to generate historical HSCF outputs if historical schema files exist.
6. Report warnings.

## When using HSCF as context

Do not load the full pack first.

Recommended loading order:

1. Load `<object>.hsp-view.json`.
2. Read `m`.
3. Read `idx.prop`.
4. Load only selected rows from `refs.props`.
5. Open enum sidecars only if enum validation is needed.
6. Load the full pack only if required.

## Typical property lookup

Given a view file:

```json
"idx": {
  "prop": {
    "email": 0,
    "lifecyclestage": 5
  }
}
```

If a task concerns `lifecyclestage`, load the row at index `5` from `refs.props`. If that row has an enum reference, open the referenced enum sidecar only if valid option values are needed.
