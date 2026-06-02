# HSCF object implementation notes

## Input

The object encoder accepts either:

```json
{"properties": []}
```

or:

```json
{"result": {"properties": []}}
```

## Output

For object key `contacts`, emit:

```text
contacts.hsp.json
contacts.hsp-view.json
parts/contacts.hsp-props.json
options/*.hsp-options.json
```

## Retrieval model

- The full profile is canonical.
- The view profile is the low-token entrypoint.
- Property rows are retrieved through `refs.props`.
- Enum sidecars are opened only when option validation is needed.

## Commands

```bash
hscf objects encode path/to/schema.json -o schema-packs/objects --object-key contacts
hscf objects property path/to/contacts.hsp-view.json email
```
