# HSCF: HubSpot schema compact format

HSCF stands for **HubSpot schema compact format**. It is a deterministic JSON-based format for representing HubSpot object schemas in a way that reduces token usage and prompt size when agents work with those schemas, while preserving source schema detail.

The practical target is simple: agents should almost never load the full HubSpot schema export. They should load a thin HSCF view file, use the property index to find relevant rows, open only those rows, and open enum sidecars only when enum validation is needed.

## What this repo is for

This repository is public reference material for humans and agents.

Use it when an agent is asked to implement HSCF in a different repository that already contains HubSpot schema exports. The agent should read this repo for:

1. The HSCF format and retrieval model.
2. A small reference encoder.
3. Example control-surface conventions such as `config/hscf.yml`.
4. Implementation instructions in `AGENTS.md`.

This repository is not meant to auto-discover and encode schemas across arbitrary repos by itself. The repo-specific discovery, wiring, and generation workflow belong in the target repository being modified.

## Repository contents

```text
.
├── docs/
│   ├── HSCF_v1_standard.md
│   ├── implementation.md
│   └── agent-quickstart.md
├── hscf/
│   ├── __init__.py
│   ├── cli.py
│   └── encode.py
├── scripts/
│   └── encode_schema.py
├── schemas/
│   ├── hscf-pack-v1.schema.json
│   └── hscf-options-v1.schema.json
├── examples/
│   ├── raw/
│   │   └── synthetic_contact_schema.json
│   └── output/
├── tests/
│   └── test_encoder.py
├── config/
│   └── hscf.example.yml
├── AGENTS.md
├── pyproject.toml
└── Makefile
```

## Core artefacts

HSCF produces these files:

```text
<object>.hsp.json                              # full profile; canonical compact pack
<object>.hsp-view.json                         # view profile; thin agent entrypoint
parts/<object>.hsp-props.json                  # property rows for selective retrieval
options/<object>.<property-key>.hsp-options.json  # enum sidecars, file-safe and deterministic
```

## Fast start

From the repository root:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e .
python -m hscf.cli encode examples/raw/synthetic_contact_schema.json -o examples/output --object-key synthetic_contact
```

This writes a full pack, view pack, property part file, and any enum sidecars. Full packs embed property rows, so `python -m hscf.cli property <object>.hsp.json <property>` also works if the sibling `parts/` file is not present.

Enum references inside a pack use the original property name in `eo` and `e`. Sidecar filenames are generated separately so they stay file-safe and deterministic even when multiple property names normalize to the same filename-safe token.

## Expected agent workflow

1. Load `<object>.hsp-view.json` first.
2. Read `m` for object metadata.
3. Use `idx.prop` to locate relevant properties.
4. Load selected rows from `refs.props`.
5. Open enum sidecars only when validating or mapping enum values.
6. Load the full pack only for audit, migration, unknown-field inspection, or regeneration.

## Implementing HSCF in another repository

Give an implementation agent this repository and ask it to implement HSCF against the target repository's HubSpot schema files. The agent should:

1. Find the latest raw HubSpot object schema exports.
2. Identify whether historical schema versions exist.
3. Add or update a control surface such as `config/hscf.yml`.
4. Generate `.hsp.json`, `.hsp-view.json`, property part files, and enum sidecars for latest schemas.
5. Offer to encode historical versions where present.
6. Report warnings; do not silently discard unknown schema data. Preserve known-but-unmodelled source fields in `x` as well.

See `AGENTS.md` and `docs/agent-quickstart.md`.

## Public repo caution

Do not commit private HubSpot sandbox schema exports, credentials, portal IDs that should not be public, sensitive property descriptions, or internal-only object metadata unless they have been reviewed for publication. This scaffold includes only synthetic fixture data.

## Specification

The formal v1 draft is in `docs/HSCF_v1_standard.md`.
