# Object quickstart

## When asked to implement HSCF

1. Read [`docs/objects/standard.md`](standard.md).
2. Locate HubSpot object schema exports.
3. Add or update `config/hscf.yml` under the `objects:` section.
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
