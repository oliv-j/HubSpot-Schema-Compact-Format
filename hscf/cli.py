from __future__ import annotations

import argparse
import json
from pathlib import Path

from .encode import encode, expand_property_row, load_json, safe_key, write_encoded
from .workflow import encode_workflow, expand_step_row, write_workflow_encoded


def _print_written(written: dict[str, str]) -> None:
    for label, path in written.items():
        print(f"{label}: {path}")


def cmd_objects_encode(args: argparse.Namespace) -> int:
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
    _print_written(written)
    warnings = result.full.get("w", [])
    if warnings:
        print(f"warnings: {len(warnings)}")
    return 0


def cmd_objects_property(args: argparse.Namespace) -> int:
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
            props = pack
        else:
            raise SystemExit(f"Property rows file not found: {props_path}")
    else:
        props = pack
    expanded = expand_property_row(props, idx[args.name])
    print(json.dumps(expanded, indent=2, ensure_ascii=False))
    return 0


def cmd_workflows_encode(args: argparse.Namespace) -> int:
    raw = load_json(args.input)
    workflow_key = safe_key(args.workflow_key) if args.workflow_key else None
    result = encode_workflow(raw, workflow_key=workflow_key)
    final_key = workflow_key or safe_key(result.full["m"].get("name") or result.full["m"].get("id") or "workflow")
    written = write_workflow_encoded(result, args.output, final_key)
    _print_written(written)
    warnings = result.full.get("w", [])
    if warnings:
        print(f"warnings: {len(warnings)}")
    return 0


def cmd_workflows_step(args: argparse.Namespace) -> int:
    pack = load_json(args.pack)
    idx = pack.get("idx", {}).get("step", {})
    if args.id not in idx:
        raise SystemExit(f"Step not found: {args.id}")
    steps_ref = pack.get("refs", {}).get("steps")
    if steps_ref:
        steps_path = Path(args.pack).parent / steps_ref
        if steps_path.exists():
            steps = load_json(steps_path)
        elif "s" in pack:
            steps = pack
        else:
            raise SystemExit(f"Step rows file not found: {steps_path}")
    else:
        steps = pack
    expanded = expand_step_row(steps, idx[args.id])
    print(json.dumps(expanded, indent=2, ensure_ascii=False))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="hscf", description="HubSpot compact format reference CLI")
    sub = parser.add_subparsers(dest="domain")

    objects = sub.add_parser("objects", help="Commands for HSCF object schema packs")
    objects_sub = objects.add_subparsers(dest="objects_command", required=True)

    obj_encode = objects_sub.add_parser("encode", help="Encode a HubSpot object schema JSON file into HSCF files")
    obj_encode.add_argument("input", help="Input HubSpot object schema JSON")
    obj_encode.add_argument("-o", "--output", default=".", help="Output directory")
    obj_encode.add_argument("--object-key", help="File-safe object key for output names")
    obj_encode.add_argument("--option-count-threshold", type=int, default=25)
    obj_encode.add_argument("--option-bytes-threshold", type=int, default=4096)
    obj_encode.set_defaults(func=cmd_objects_encode)

    obj_property = objects_sub.add_parser("property", help="Expand one property row from a view or full object pack")
    obj_property.add_argument("pack", help="Path to .hsp-view.json or .hsp.json")
    obj_property.add_argument("name", help="Property name")
    obj_property.set_defaults(func=cmd_objects_property)

    workflows = sub.add_parser("workflows", help="Commands for HWCF workflow packs")
    wf_sub = workflows.add_subparsers(dest="workflows_command", required=True)

    wf_encode = wf_sub.add_parser("encode", help="Encode a HubSpot workflow JSON file into HWCF files")
    wf_encode.add_argument("input", help="Input HubSpot workflow JSON")
    wf_encode.add_argument("-o", "--output", default=".", help="Output directory")
    wf_encode.add_argument("--workflow-key", help="File-safe workflow key for output names")
    wf_encode.set_defaults(func=cmd_workflows_encode)

    wf_step = wf_sub.add_parser("step", help="Expand one workflow step row from a view or full workflow pack")
    wf_step.add_argument("pack", help="Path to .hwp-view.json or .hwp.json")
    wf_step.add_argument("id", help="Workflow step ID")
    wf_step.set_defaults(func=cmd_workflows_step)

    legacy_encode = sub.add_parser("encode", help=argparse.SUPPRESS)
    legacy_encode.add_argument("input")
    legacy_encode.add_argument("-o", "--output", default=".")
    legacy_encode.add_argument("--object-key")
    legacy_encode.add_argument("--option-count-threshold", type=int, default=25)
    legacy_encode.add_argument("--option-bytes-threshold", type=int, default=4096)
    legacy_encode.set_defaults(func=cmd_objects_encode)

    legacy_property = sub.add_parser("property", help=argparse.SUPPRESS)
    legacy_property.add_argument("pack")
    legacy_property.add_argument("name")
    legacy_property.set_defaults(func=cmd_objects_property)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if not hasattr(args, "func"):
        parser.print_help()
        return 1
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
