# Agent instructions for implementing HubSpot compact formats

Use these instructions when an agent is asked to implement compact HubSpot retrieval artefacts in a repository that already contains HubSpot exports.

## Objective

Identify which optimisation family the target repository needs, then implement the matching compact artefacts:

- **HSCF** for HubSpot object schema exports
- **HWCF** for HubSpot workflow exports

If the repository contains both domains, implement them as sibling tracks under one shared control surface.

## Required behaviour

1. Identify whether the task concerns object schemas, workflows, or both.
2. Locate raw HubSpot exports. Accept either:
   - raw exports; or
   - wrapped exports containing the useful payload under `result`.
3. Determine the latest version for each object or workflow.
4. Detect whether historical versions exist.
5. Add or update a control surface, normally `config/hscf.yml`, with separate top-level sections by domain.
6. Generate compact files for latest exports.
7. Offer to encode historical versions if they exist.
8. Preserve unknown fields in `x` and emit compact warnings in `w`.
9. Do not silently drop data.
10. Do not commit secrets, HubSpot API keys, private raw exports, or credentials.

## Recommended implementation steps

1. Read [`docs/compact-format-family.md`](docs/compact-format-family.md).
2. Choose the domain-specific quickstart:
   - objects: [`docs/objects/agent-quickstart.md`](docs/objects/agent-quickstart.md)
   - workflows: [`docs/workflows/agent-quickstart.md`](docs/workflows/agent-quickstart.md)
3. Inspect the target repository for likely export directories:
   - `schemas/`
   - `schema/`
   - `hubspot/schemas/`
   - `workflows/`
   - `data/hubspot/`
   - `exports/`
4. For each relevant file, identify:
   - stable key
   - name
   - updated timestamp
   - whether it is latest or historical
5. Create or update `config/hscf.yml`.
6. Add generation commands to the target repository.
7. Run tests or add a smoke test.
8. Summarise warnings.

## Domain commands

### Objects

```bash
python -m hscf.cli objects encode path/to/schema.json -o schema-packs/objects --object-key contacts
```

### Workflows

```bash
python -m hscf.cli workflows encode path/to/workflow.json -o schema-packs/workflows --workflow-key lead_nurture
```

## Warning policy

Treat warnings as reviewable, not fatal, unless an error prevents indexing.

Severity codes:

```text
i = info
w = warning
e = error
```

If new HubSpot fields are encountered, preserve them under `x` and warn. If known source fields are not modelled as dedicated metadata, row columns, dictionaries, flags, hints, or sidecar content, preserve them under `x` without warning unless they are also unknown. If a required stable identifier is missing for a row, do not index that row and emit an error.

## Prompt loading order for downstream agents

### Objects

1. Load the view file.
2. Read metadata `m`.
3. Read `idx.prop`.
4. Retrieve selected property rows from `refs.props`.
5. Open enum sidecars only for enum validation.
6. Load associations only when association logic is needed.
7. Load the full pack only for audit, migration, unknown fields, or decoding.

### Workflows

1. Load the view file.
2. Read metadata `m`.
3. Read `idx.step`.
4. Retrieve selected step rows from `refs.steps`.
5. Load the full pack only for audit, goals, enrollment logic, unknown fields, or decoding.

## HubSpot Agent CLI environment policy

Use these rules whenever HubSpot Agent CLI access is needed alongside compact-format work in this repository.

- Use `hubspot-sb` for sandbox work and `hubspot-prod` for production work.
- Do not use bare `hubspot` in routine repo workflows.
- Default to sandbox unless the task explicitly requires production.
- Access is read-only for now unless the user explicitly changes that constraint.
- Always run `whoami` before using the Agent CLI for meaningful work.
- For any future write-capable workflow, run `whoami` again immediately before the write.
- Treat ambiguous environment requests as blocked until clarified.

### Local wrapper locations

- Production wrapper: `~/.local/bin/hubspot-prod`
- Sandbox wrapper: `~/.local/bin/hubspot-sb`
- Underlying binary: `/Users/oliver.jobson/.hubspot/bin/hubspot`

### Auth isolation model

- Prod auth home: `~/.hubspot-agent/prod`
- Sandbox auth home: `~/.hubspot-agent/sandbox`
- Current observed macOS auth cache shape: `~/Library/Application Support/hubspot/auth.json`

### Local HubSpot skill bundle

HubSpot Agent CLI operating guidance is available in `.agents/skills/`. These skill files are local instruction bundles for common HubSpot tasks such as CRM lookup, bulk operations, workflow automation, and data quality work. Agents should consult the relevant `SKILL.md` before using the HubSpot Agent CLI for those tasks.

For this workspace, the installed local skill bundle lives at:

- `/Users/oliver.jobson/Documents/Codex/2026-06-02/run-this-npx-skills-add-hubspot/.agents/skills`
