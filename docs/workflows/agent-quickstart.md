# Workflow quickstart

## When asked to implement HWCF

1. Read [`docs/workflows/standard.md`](standard.md).
2. Locate HubSpot workflow exports.
3. Add or update `config/hscf.yml` under the `workflows:` section.
4. Generate HWCF outputs for latest workflow files.
5. Offer to generate historical HWCF outputs if historical workflow files exist.
6. Report warnings.

## When using HWCF as context

Do not load the full pack first.

Recommended loading order:

1. Load `<workflow>.hwp-view.json`.
2. Read `m`.
3. Read `idx.step`.
4. Load only selected rows from `refs.steps`.
5. Load the full pack only if goals, enrollment logic, or unknown-field inspection are needed.
