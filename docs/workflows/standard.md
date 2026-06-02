# HWCF workflow pack format

HWCF is the **HubSpot workflow compact format** for HubSpot workflow exports, especially HubSpot Workflows v4 payloads built around `actions[]`.

## Purpose

HWCF lets agents inspect workflow structure without loading the full raw workflow export into context.

The practical target is:

1. Load a thin workflow view file first.
2. Read metadata and indexes.
3. Retrieve only the workflow action rows needed for the task.
4. Open the full pack only for audit, enrollment logic, or unknown-field inspection.

## Design principles

1. Programmatic first
2. Sparse retrieval by default
3. No silent data loss
4. Stable output for stable input
5. Real HubSpot v4 action-graph semantics over synthetic workflow abstractions

## Common artefacts

```text
<workflow>.hwp.json
<workflow>.hwp-view.json
parts/<workflow>.hwp-steps.json
```

The `steps` naming is retained for retrieval continuity, but the canonical HubSpot v4 source model is action-based.

## Input expectations

The encoder accepts:

1. a direct workflow object containing `actions`; or
2. a wrapper object containing `result.actions`.

HubSpot v4 `actions[]` is the required executable graph source for HWCF input.

## Profiles

### Full profile

Canonical compact representation for validation, audit, decoding, and regeneration.

Required top-level keys:

```text
v, kind, profile, m, d, sk, s, idx, refs, x, wk, w, raw
```

### View profile

Low-token agent entrypoint.

Required top-level keys:

```text
v, kind, profile, m, sk, idx, refs, raw
```

The view profile should normally omit:

```text
s, x, w
```

## Metadata block: `m`

Workflow metadata should prioritize first-pass retrieval:

```text
id
name
type
flowType
enabled
desc
createdAt
updatedAt
revisionId
uuid
objectTypeId
startActionId
nextAvailableActionId
crmObjectCreationStatus
canEnrollFromSalesforce
stepCount
excludedActionCount
goalCount
hasEnrollmentCriteria
hasUnenrollmentCriteria
suppressionListCount
```

## Action rows

Default `sk`:

```text
id, n, t, next, branch, timing, asset, goal, f, hints, x
```

Meanings:

```text
id      stable workflow node ID, sourced from actionId for HubSpot v4 actions
n       action name or label when available
t       normalized action type dictionary ID
next    ordered outbound action IDs
branch  compact branch summary for static/list/AB/default branches
timing  wait or delay summary
asset   action reference summary such as content, flow, property, runtime, or field counts
goal    compact input-value or goal-like summary when applicable
f       action flag bitset
hints   compact retrieval hints
x       preserved source fields not directly modeled
```

Rows may omit trailing nulls. Readers must restore trailing nulls back to the length of `sk`.

## Graph rules

- Source row order remains source order from the HubSpot payload.
- Traversal should use `next`.
- `next` may be populated from:
  - `connection.nextActionId`
  - `staticBranches[*].connection.nextActionId`
  - `defaultBranch.nextActionId`
  - `listBranches[*].connection.nextActionId`
  - `testBranches[*].connection.nextActionId`

## Indexes

HWCF v1 defines these indexes:

```text
idx.step   maps normalized action IDs to row indexes
idx.type   maps normalized action types to action IDs
```

## Warnings

Compact warning tuples:

```json
"wk": ["sev", "code", "path", "msg"]
```

Severity codes:

```text
i = info
w = warning
e = error
```

Warnings should indicate invalid or unusual shapes, not normal HubSpot v4 structure.

The view profile should surface compact degradation state through metadata such as `excludedActionCount`, while the full profile retains detailed warning tuples in `w`.

## Preservation rules

- Unknown workflow and action fields must be preserved under `x`.
- Known-but-unmodeled workflow configuration should also be preserved under `x`.
- `actionId` is required for HWCF action identity.
- If an action is missing `actionId`, it must be excluded and the encoder must emit an error.
- If multiple actions share the same `actionId`, only the first may be emitted; later duplicates must be excluded and the encoder must emit an error.

## Recommended retrieval order

1. Load `<workflow>.hwp-view.json`.
2. Read `m`.
3. Read `idx.step` and optionally `idx.type`.
4. Retrieve selected rows from `refs.steps`.
5. Load the full pack only when enrollment logic, warnings, or preserved unknown fields are needed.
