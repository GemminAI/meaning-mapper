# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Gemmina Intelligence LLC.

"""Meaning Mapper CLI — map raw observations to HEXT Observation Objects."""

from __future__ import annotations

import argparse
import json
import sys
import warnings
from pathlib import Path

from adapters import list_adapters
from semantic_annotator.pipeline import annotate
from validation import ValidationError

from meaning_mapper.version import __version__


def build_parser(prog: str = "meaning-mapper") -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog=prog,
        description=(
            "Meaning Mapper — map raw observations into HEXT Observation Objects. "
            "Deterministic. Stateless. Reference service surface."
        ),
    )
    parser.add_argument("input", nargs="?", help="Input file path (or - for stdin)")
    parser.add_argument(
        "-t",
        "--type",
        dest="source_type",
        help="Adapter type hint (json, text, markdown, csv, rss, ...)",
    )
    parser.add_argument(
        "-o",
        "--output",
        help="Write JSON to this path instead of stdout",
    )
    parser.add_argument(
        "--list-adapters",
        action="store_true",
        help="List available adapters and exit",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"meaning-mapper {__version__}",
    )
    return parser


def _run(argv: list[str] | None, prog: str) -> int:
    parser = build_parser(prog=prog)
    args = parser.parse_args(argv)

    if args.list_adapters:
        for name in list_adapters():
            print(name)
        return 0

    if not args.input:
        parser.error("input is required (file path or -)")

    try:
        if args.input == "-":
            raw = sys.stdin.buffer.read()
            filename = None
            source_ref = "stdin://"
        else:
            path = Path(args.input)
            raw = path.read_bytes()
            filename = path.name
            source_ref = path.resolve().as_uri()

        obj = annotate(
            raw,
            source_type=args.source_type,
            source_ref=source_ref,
            filename=filename,
        )
    except (OSError, ValidationError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    payload = json.dumps(obj, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        Path(args.output).write_text(payload, encoding="utf-8")
    else:
        sys.stdout.write(payload)
    return 0


def main(argv: list[str] | None = None) -> int:
    return _run(argv, prog="meaning-mapper")


def main_compat(argv: list[str] | None = None) -> int:
    warnings.warn(
        "The 'semantic-annotator' CLI entry point is deprecated. Use 'meaning-mapper' instead. "
        "See https://github.com/GemminAI/meaning-mapper/blob/main/docs/MIGRATION.md",
        DeprecationWarning,
        stacklevel=2,
    )
    return _run(argv, prog="semantic-annotator")
