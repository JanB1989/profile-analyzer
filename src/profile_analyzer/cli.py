"""Standalone command line; paths are relative to the caller's working directory."""

from __future__ import annotations

import argparse
from pathlib import Path

from profile_analyzer import __version__
from profile_analyzer.analyzer import host_path, new_report_directory, read_capture, write_report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="profile-analyzer",
        description="Create an offline EU5 profiler report from a logs folder or CSV.",
    )
    parser.add_argument("input", help="Logs folder, profiler CSV, or an earlier report folder.")
    parser.add_argument("--output", "-o", default="reports", help="Parent of timestamped reports (default: ./reports).")
    parser.add_argument("--label", help="Capture name (default: input folder name).")
    parser.add_argument("--baseline", help="Earlier logs, CSV, or report to compare against.")
    parser.add_argument("--game-root", help="Optional game installation or game script directory.")
    parser.add_argument("--mod-root", action="append", default=[], help="Optional mod root; repeat in load order.")
    parser.add_argument("--source", action="append", default=[], metavar="NAME=PATH",
                        help="Optional named source root; repeat in load order, after --mod-root.")
    parser.add_argument("--time-unit", choices=("raw", "seconds", "milliseconds", "microseconds"),
                        default="raw", help="Unit of input values, if independently known (default: raw).")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    return parser


def source_roots(args, base: Path) -> list[tuple[str, Path]]:
    roots = []
    if args.game_root:
        roots.append(("vanilla", host_path(args.game_root, base)))
    for value in args.mod_root:
        root = host_path(value, base)
        roots.append((root.name or "mod", root))
    for value in args.source:
        name, separator, path = value.partition("=")
        if not separator or not name.strip() or not path.strip():
            raise ValueError("--source must be NAME=PATH")
        roots.append((name, host_path(path, base)))
    for name, root in roots:
        if not root.is_dir():
            raise ValueError(f"Source root {name!r} is not a directory: {root}")
    return roots


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    base = Path.cwd()
    try:
        roots = source_roots(args, base)
        input_path = host_path(args.input, base)
        capture = read_capture(input_path)
        capture["label"] = args.label or capture["label"]
        baseline = read_capture(host_path(args.baseline, base)) if args.baseline else None
        if baseline and not (capture["datasets"].keys() & baseline["datasets"].keys()):
            raise ValueError("Capture and baseline have no matching profiler views")
        output = new_report_directory(host_path(args.output, base), capture["label"])
        print(f"Input: {input_path}", flush=True)
        print(f"Output: {output}", flush=True)
        print(f"Reading {sum(d['raw_rows'] for d in capture['datasets'].values()):,} rows; "
              f"resolving {len(roots)} source roots.", flush=True)
        report = write_report(capture, baseline, roots, output, args.time_unit)
    except KeyboardInterrupt:
        return 130
    except (OSError, ValueError, KeyError) as exc:
        parser.exit(2, f"profile-analyzer: {exc}\n")
    for scope, dataset in report["datasets"].items():
        print(f"{scope}: {dataset['raw_rows']:,} rows, {dataset['duplicates']:,} duplicate locations, "
              f"{dataset['resolved']:,} source-resolved, {len(dataset['edges']):,} inferred edges")
    print(f"Report: {output / 'index.html'}")
    print(f"Data: {output / 'profile.json'}")
    print("Times retain dump units. Graph edges are source-inferred, not recorded call stacks.")
    if report["warnings"]:
        print(f"Source parse warnings: {len(report['warnings'])} (see report)")
    return 0
