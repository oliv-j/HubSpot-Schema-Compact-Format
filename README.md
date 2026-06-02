# HubSpot compact formats

This repository is public reference material for **HubSpot compact formats**: low-token, deterministic JSON artefacts that let agents and tools work with HubSpot exports through sparse retrieval instead of loading full raw JSON every time.

Today the repo includes two domain tracks:

- **HSCF**: HubSpot schema compact format for object schemas
- **HWCF**: HubSpot workflow compact format for workflows

The practical goal is the same across both tracks:

1. Load a thin view file first.
2. Read metadata and indexes.
3. Retrieve only the rows needed for the current task.
4. Open full packs only for audit, regeneration, or unknown-field inspection.

## What this repo is for

Use this repository as a **reference pattern plus reference CLI** when an agent or engineer needs to add compact HubSpot retrieval artefacts to another codebase that already contains HubSpot exports.

This repository is not meant to auto-discover and encode arbitrary customer data by itself. The target repository should own:

- export discovery
- latest-vs-historical selection
- generation commands
- CI wiring
- publication decisions

## Choose your path

| I need... | Start here |
| --- | --- |
| Object schema retrieval | [`docs/objects/standard.md`](docs/objects/standard.md) |
| Workflow retrieval | [`docs/workflows/standard.md`](docs/workflows/standard.md) |
| A shared adoption model for both | [`docs/compact-format-family.md`](docs/compact-format-family.md) |
| Agent implementation instructions | [`AGENTS.md`](AGENTS.md) |

## Repository contents

```text
.
├── docs/
│   ├── compact-format-family.md
│   ├── objects/
│   └── workflows/
├── examples/
│   ├── objects/
│   └── workflows/
├── hscf/
│   ├── cli.py
│   ├── encode.py
│   └── workflow.py
├── schemas/
│   ├── objects/
│   └── workflows/
├── config/
│   └── hscf.example.yml
├── tests/
│   └── test_encoder.py
└── scripts/
    └── encode_schema.py
```

## Shared design rules

- Sparse retrieval by default
- Deterministic output from deterministic code
- No silent data loss
- Unknown fields preserved under `x`
- Compact warnings emitted under `w`
- Domain-specific contracts instead of forcing everything into object-schema terms

## Domain artefacts

### Objects: HSCF

```text
<object>.hsp.json
<object>.hsp-view.json
parts/<object>.hsp-props.json
options/<object>.<property>.hsp-options.json
```

### Workflows: HWCF

```text
<workflow>.hwp.json
<workflow>.hwp-view.json
parts/<workflow>.hwp-steps.json
```

## Fast start

From the repository root:

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -e .
python3 -m hscf.cli objects encode examples/objects/raw/synthetic_contact_schema.json -o examples/objects/output --object-key synthetic_contact
python3 -m hscf.cli workflows encode examples/workflows/raw/1743507592.workflow.json -o examples/workflows/output --workflow-key 1743507592
```

## CLI surface

```bash
hscf objects encode ...
hscf objects property ...
hscf workflows encode ...
hscf workflows step ...
```

Legacy top-level `encode` and `property` commands are retained as object-schema aliases for compatibility.

## Adopting this in another repository

The recommended downstream pattern is:

1. Copy the domain-specific retrieval model you need.
2. Add a shared control surface such as [`config/hscf.example.yml`](config/hscf.example.yml).
3. Add repo-specific discovery logic for latest and historical exports.
4. Wire generation commands into that repository.
5. Publish only reviewed compact artefacts, not raw private exports.

For mixed repos, keep both optimisations in one control surface with separate top-level sections such as `objects:` and `workflows:`.

## Public repo caution

Do not commit private HubSpot exports, secrets, API keys, internal-only descriptions, or sensitive portal metadata unless they have been reviewed for publication. This repository includes reviewed reference fixture data only.

## HubSpot Agent CLI

This repo uses two wrapper commands for HubSpot Agent CLI access:

- `hubspot-sb` for sandbox
- `hubspot-prod` for production

Do not use bare `hubspot` for normal repo workflows.

Before running HubSpot commands, always verify identity:

```bash
hubspot-sb whoami
hubspot-prod whoami
```

Default to sandbox unless a task explicitly requires production. Current operating mode is read-only unless the user explicitly asks to change that.

Local wrapper locations:

- `~/.local/bin/hubspot-sb`
- `~/.local/bin/hubspot-prod`

Underlying binary:

- `/Users/oliver.jobson/.hubspot/bin/hubspot`

Auth is isolated by `HOME`:

- sandbox: `~/.hubspot-agent/sandbox`
- production: `~/.hubspot-agent/prod`

HubSpot task guidance is also available under `.agents/skills/`. Read the relevant `SKILL.md` before performing HubSpot Agent CLI tasks. In this workspace, that bundle is installed at `/Users/oliver.jobson/Documents/Codex/2026-06-02/run-this-npx-skills-add-hubspot/.agents/skills`.
