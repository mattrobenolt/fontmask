"""Command-line interface for fontmask."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from fontTools.ttLib import TTFont

from . import __version__
from .analysis import analyze
from .patcher import patch_font
from .rules import RuleSet

LICENSE_NOTE = (
    "The patched font contains OFL-licensed mask rules from Obel Mono. "
    "Check the target font's license before distribution."
)


def _load_font(path: str, font_number: int):
    return TTFont(path, fontNumber=font_number)


def _print_analysis(path: str, font, rules: RuleSet) -> None:
    analysis = analyze(font, rules)
    print(f"Font: {path}")
    print(f"Outlines: {analysis.outlines}")
    print(f"Variable: {'yes' if analysis.variable else 'no'}")
    print(f"Monospaced: {'yes' if analysis.monospace else 'no'}")
    print(f"UPM: {analysis.upm}")
    print(f"Glyphs: {analysis.glyph_count}")
    print(f"cmap entries: {analysis.cmap_count}")
    print(f"GSUB features: {', '.join(analysis.features) or '(none)'}")
    print(f"Existing ccmp: {'yes' if analysis.has_ccmp else 'no'}")
    print(f"Already masked: {'yes' if analysis.already_masked else 'no'}")
    print(f"Rule glyphs present: {analysis.encoded_present}")
    print(f"Rule glyphs missing: {len(analysis.encoded_missing)}")
    print(f"Note glyphs to add: {len(analysis.specials)}")
    if analysis.encoded_missing:
        print("Missing: " + ", ".join(analysis.encoded_missing))


def cmd_inspect(args) -> int:
    font = _load_font(args.font, args.font_number)
    rules = RuleSet.load(args.rules)
    analysis = analyze(font, rules)
    if args.json:
        print(json.dumps(analysis.as_dict(), indent=2))
    else:
        _print_analysis(args.font, font, rules)
    return 0


def cmd_patch(args) -> int:
    try:
        plan = patch_font(
            args.font,
            args.output,
            family=args.family,
            style=args.style,
            instance=args.instance,
            rules_path=args.rules,
            font_number=args.font_number,
            dry_run=args.dry_run,
        )
    except (ValueError, NotImplementedError) as exc:
        print(f"fontmask: {exc}", file=sys.stderr)
        return 1
    summary = plan.summary()
    if args.json:
        print(json.dumps(summary, indent=2))
    else:
        print(f"Family: {summary['family']}")
        print(f"Style: {summary['style']}")
        if summary["instance"]:
            print(
                "Instance: "
                + ", ".join(f"{k}={v}" for k, v in summary["instance"].items())
            )
        print(
            f"Glyphs added: {summary['glyphs_added']} ({summary['note_glyphs']} notes, {summary['mask_glyphs']} masks)"
        )
        widths = {
            name: widths for name, widths in summary["mask_widths"].items() if widths
        }
        print(f"Mask classes: {len(widths)}")
        for name, values in sorted(widths.items()):
            print(f"  {name}: {len(values)} width(s)")
        if summary["warnings"]:
            print("Warnings:")
            for warning in summary["warnings"]:
                print(f"  {warning}")
        if args.dry_run:
            print("Dry run: no file written.")
        else:
            print(f"Wrote: {args.output}")
        print(LICENSE_NOTE)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="fontmask",
        description="Add Obel Mono-style secret masking to an existing font.",
    )
    parser.add_argument(
        "--version", action="version", version=f"fontmask {__version__}"
    )
    sub = parser.add_subparsers(dest="command", required=True)

    inspect_parser = sub.add_parser("inspect", help="inspect a target font")
    inspect_parser.add_argument("font")
    inspect_parser.add_argument(
        "--font-number", type=int, default=0, help="face index for TTC files"
    )
    inspect_parser.add_argument(
        "--rules", help="path to a rules font; defaults to the bundled Obel Mono Masked"
    )
    inspect_parser.add_argument("--json", action="store_true")
    inspect_parser.set_defaults(func=cmd_inspect)

    patch_parser = sub.add_parser("patch", help="patch a target font")
    patch_parser.add_argument("font")
    patch_parser.add_argument(
        "-o", "--output", help="output path; defaults to <name>-masked.<ext>"
    )
    patch_parser.add_argument(
        "--family", help="output family name; defaults to '<family> Masked'"
    )
    patch_parser.add_argument(
        "--style", help="output style name; defaults to the source style"
    )
    patch_parser.add_argument(
        "--instance", help="variable-font instance, e.g. wght=400 or a named instance"
    )
    patch_parser.add_argument(
        "--font-number", type=int, default=0, help="face index for TTC files"
    )
    patch_parser.add_argument(
        "--rules", help="path to a rules font; defaults to the bundled Obel Mono Masked"
    )
    patch_parser.add_argument(
        "--dry-run", action="store_true", help="report the plan without writing a file"
    )
    patch_parser.add_argument("--json", action="store_true")
    patch_parser.set_defaults(func=cmd_patch)
    return parser


def main(argv=None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command == "patch" and not args.output and not args.dry_run:
        path = Path(args.font)
        args.output = str(path.with_name(f"{path.stem}-masked{path.suffix}"))
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
