# Changelog

## 0.1.1

- Preserve known-but-unmodelled source fields in canonical packs instead of dropping them during encode.
- Add CLI fallback so `property` can inspect a standalone full `.hsp.json` when the sibling property part file is missing.
- Add regression tests for canonical preservation and standalone full-pack property lookup.

## 0.1.0

- Initial public scaffold for HSCF v1.
- Includes draft spec, reference encoder, CLI, synthetic fixture, tests, and agent instructions.
