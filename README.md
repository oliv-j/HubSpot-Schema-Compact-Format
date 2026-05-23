# HSCF: HubSpot schema compact format

HSCF stands for **HubSpot schema compact format**. It is a deterministic JSON-based format for representing HubSpot object schemas in a way that reduces token usage when agents need to read, validate, or reason about those schemas, while still preserving the important source detail.

The practical target is simple: agents should almost never load the full HubSpot schema export into context. They should load a thin HSCF view file, use the property index to find relevant rows, open only those rows, and open enum sidecars only when enum validation is needed. The point is to keep prompts small and retrieval sparse so schema-heavy tasks stay cheaper and more reliable.

## What this repo is for

This repository is intended to be **public reference material** for humans and agents.

Its primary purpose is:

1. Define the HSCF format.
2. Provide a small reference encoder.
3. Give implementation agents enough documentation and examples to add HSCF support inside a different repository that already contains HubSpot schema exports.

This repository is **not** trying to be a complete repo-scanning product that automatically discovers schema files across arbitrary repositories. Instead, it gives downstream agents:

1. The format specification.
2. A reference Python implementation of the encoder.
3. Example control-surface conventions such as `config/hscf.yml`.
4. Prompting guidance in `AGENTS.md` for implementing HSCF elsewhere.

When an agent is told to use this repo in another codebase, the expected workflow is:

1. Read the spec and implementation notes here.
2. Inspect the target repository for its actual schema layout.
3. Add the appropriate control surface in that target repository.
4. Wire the reference encoder or equivalent logic into that target repository's scripts, tests, and generation flow.

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
<object>.hsp.json                       # full profile; canonical compact pack
<object>.hsp-view.json                  # view profile; thin agent entrypoint
parts/<object>.hsp-props.json           # property rows for selective retrieval
options/<object>.<property>.hsp-options.json  # enum sidecars, when needed
```

## Fast start

From the repository root:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e .
python -m hscf.cli encode examples/raw/synthetic_contact_schema.json -o examples/output --object-key synthetic_contact
```

This writes a full pack, view pack, property part file, and any enum sidecars.

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
6. Report warnings; do not silently discard unknown schema data.

See `AGENTS.md` and `docs/agent-quickstart.md`.

The discovery of latest schemas, historical versions, and repo-specific generation commands happens in the **target repository being modified**, not in this public reference repository.

## Public repo caution

Do not commit private HubSpot sandbox schema exports, credentials, portal IDs that should not be public, sensitive property descriptions, or internal-only object metadata unless they have been reviewed for publication. This scaffold includes only synthetic fixture data.

## Specification

The formal v1 draft is in `docs/HSCF_v1_standard.md`.
