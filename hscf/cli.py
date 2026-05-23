from __future__ import annotations

import argparse
import json
from pathlib import Path

from .encode import encode, expand_property_row, load_json, safe_key, write_encoded


def cmd_encode(args: argparse.Namespace) -> int:
    raw = load_json(args.input)
    object_key = safe_key(args.object_key) if args.object_key else None
    result = encode(
        raw,
        object_key=object_key,
        option_count_threshold=args.option_count_threshold,
        option_bytes_threshold=args.option_bytes_threshold,
    )
    final_key = object_key or safe_key(result.full["m"].get("fqn") or result.full["m"].get("name") or "schema")
    written = write_encoded(result, args.output, final_key)
    for label, path in written.items():
        print(f"{label}: {path}")
    warnings = result.full.get("w", [])
    if warnings:
        print(f"warnings: {len(warnings)}")
    return 0


def cmd_property(args: argparse.Namespace) -> int:
    pack = load_json(args.pack)
    idx = pack.get("idx", {}).get("prop", {})
    if args.name not in idx:
        raise SystemExit(f"Property not found: {args.name}")
    props_ref = pack.get("refs", {}).get("props")
    if props_ref:
        props_path = Path(args.pack).parent / props_ref
        if props_path.exists():
            props = load_json(props_path)
        elif "p" in pack:
            # Full packs embed property rows, so they remain inspectable even
            # when copied without their sibling parts directory.
            props = pack
        else:
            raise SystemExit(f"Property rows file not found: {props_path}")
    else:
        props = pack
    expanded = expand_property_row(props, idx[args.name])
    print(json.dumps(expanded, indent=2, ensure_ascii=False))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="hscf", description="HSCF reference CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    enc = sub.add_parser("encode", help="Encode a HubSpot schema JSON file into HSCF files")
    enc.add_argument("input", help="Input HubSpot schema JSON")
    enc.add_argument("-o", "--output", default=".", help="Output directory")
    enc.add_argument("--object-key", help="File-safe object key for output names")
    enc.add_argument("--option-count-threshold", type=int, default=25)
    enc.add_argument("--option-bytes-threshold", type=int, default=4096)
    enc.set_defaults(func=cmd_encode)

    prop = sub.add_parser("property", help="Expand one property row from a view or full pack")
    prop.add_argument("pack", help="Path to .hsp-view.json or .hsp.json")
    prop.add_argument("name", help="Property name")
    prop.set_defaults(func=cmd_property)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
