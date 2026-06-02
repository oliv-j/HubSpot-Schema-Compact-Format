# HubSpot compact-format family

This repository documents a **family of compact HubSpot retrieval formats** that share the same operating model:

- deterministic JSON output
- thin view files as the normal entrypoint
- row-based selective retrieval
- full packs reserved for audit and regeneration
- no silent data loss

## When to use which track

Use the **object** track when the source material is HubSpot object schema exports with `properties` and optional `associations`.

Use the **workflow** track when the source material is workflow exports with ordered steps, transitions, branch logic, or enrollment logic.

Use **both** when a downstream repository needs agents to reason about object structure and workflow automation in the same project.

## Shared repo design

For a repository that adopts both formats, prefer one shared control surface:

```yaml
version: 1

objects:
  schemas: []

workflows:
  workflows: []
```

Design rules:

1. Top-level sections should be domain names.
2. Each domain should use its own row model and retrieval vocabulary.
3. Output directories should be partitioned by domain.
4. Agent instructions should route to the correct domain-specific quickstart before implementation begins.

## Domain references

- Objects: [`docs/objects/standard.md`](objects/standard.md)
- Workflows: [`docs/workflows/standard.md`](workflows/standard.md)

## Naming guidance

- **HSCF** refers to the object schema compact format.
- **HWCF** refers to the workflow compact format.
- “HubSpot compact formats” refers to the umbrella family.

Do not force workflow data into object-oriented contracts such as `properties`, `idx.prop`, or `.hsp-view.json`.
