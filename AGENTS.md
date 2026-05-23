# Agent instructions for implementing HSCF

Use these instructions when an agent is asked to implement HSCF in a repository that already contains HubSpot object schema exports.

## Objective

Implement HSCF generation for the repository's HubSpot object schema files.

The output should be low-token schema packs that agents can consume through sparse retrieval:

```text
<object>.hsp.json
<object>.hsp-view.json
parts/<object>.hsp-props.json
options/<object>.<property>.hsp-options.json
```

## Required behaviour

1. Locate raw HubSpot schema files. Accept either:
   - raw schema objects containing `properties`; or
   - wrapped exports containing `result.properties`.
2. Determine the latest schema version for each object.
3. Detect whether historical schema versions exist.
4. Add or update a control surface, normally `config/hscf.yml`.
5. Generate HSCF files for latest schemas.
6. Offer to encode historical schema versions if they exist.
7. Preserve unknown fields in `x` and emit compact warnings in `w`.
8. Do not silently drop data.
9. Do not commit secrets, HubSpot API keys, private raw schema exports, or credentials.

## Recommended implementation steps

1. Read `docs/HSCF_v1_standard.md`.
2. Inspect the target repository for likely schema directories:
   - `schemas/`
   - `schema/`
   - `hubspot/schemas/`
   - `data/hubspot/`
   - `exports/`
3. For each schema file, identify:
   - object type ID
   - fully qualified name
   - object name
   - updated timestamp
   - whether it is latest or historical
4. Create or update `config/hscf.yml`.
5. Add a generation command to the repo, for example:

```bash
python -m hscf.cli encode path/to/schema.json -o schema-packs --object-key contacts
```

6. Run tests or add a smoke test.
7. Summarise all warnings.

## Warning policy

Treat warnings as reviewable, not fatal, unless an error prevents indexing.

Severity codes:

```text
i = info
w = warning
e = error
```

If new HubSpot fields are encountered, preserve them under `x` and warn. If a property is missing a usable `name`, do not index that property and emit an error.

## Prompt loading order for downstream agents

1. Load the view file.
2. Read metadata `m`.
3. Read `idx.prop`.
4. Retrieve selected property rows from `refs.props`.
5. Open enum sidecars only for enum validation.
6. Load associations only when association logic is needed.
7. Load the full pack only for audit, migration, unknown fields, or decoding.
