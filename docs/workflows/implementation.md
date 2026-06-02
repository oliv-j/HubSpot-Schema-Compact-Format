# HWCF workflow implementation notes

## Input

The workflow encoder accepts either:

```json
{"actions": []}
```

or:

```json
{"result": {"actions": []}}
```

HubSpot Workflows v4 should be modeled from `actions`.

## Output

For workflow key `lead_nurture`, emit:

```text
lead_nurture.hwp.json
lead_nurture.hwp-view.json
parts/lead_nurture.hwp-steps.json
```

## Retrieval model

- The full profile is canonical.
- The view profile is the low-token entrypoint.
- The view metadata should expose compact degradation state such as `excludedActionCount`.
- Action rows are retrieved through `refs.steps`.
- `idx.step` is the primary lookup index and should contain normalized action IDs.
- `idx.type` supports fast type-based retrieval.
- The full pack is loaded only for audit, enrollment logic, warnings, and unknown-field inspection.

## Normalization guidance

Model these HubSpot v4 workflow concepts directly where present:

- action identity from `actionId`
- graph edges from connection and branch targets
- branch summaries from static/list/AB/default branches
- waits and delays from `fields.delta` and `fields.time_unit`
- email sends from `fields.content_id`
- workflow triggers from `fields.flow_id`
- property updates from `fields.property_name`
- custom code summaries from `runtime`, `inputFields`, `outputFields`, and secret references

Actions missing `actionId` and later duplicate `actionId` entries should be excluded from emitted rows and indexes while producing explicit warnings in the full pack.

Preserve unfamiliar nested workflow configuration in `x` rather than flattening it away silently.

## Commands

```bash
hscf workflows encode path/to/workflow.json -o schema-packs/workflows --workflow-key lead_nurture
hscf workflows step path/to/lead_nurture.hwp-view.json 30
```
