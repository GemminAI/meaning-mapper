# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Gemmina Intelligence LLC.

"""Meaning Mapper CLI — SA005 annotate + optional HEXT normalize."""

from __future__ import annotations

import argparse
import json
import sys
import warnings
from pathlib import Path
from typing import Any

from meaning_mapper.engine.deterministic import DeterministicAnnotatorEngine
from meaning_mapper.runtime_bridge import StandardRuntimeBridge
from meaning_mapper.version import __version__


def build_parser(prog: str = "meaning-mapper") -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog=prog,
        description=(
            "Meaning Mapper — RFC-SA001–SA005 reference service CLI. "
            "Maps measured observations to AnnotationView wire format."
        ),
    )
    sub = parser.add_subparsers(dest="command")

    annotate_p = sub.add_parser("annotate", help="Produce SA005 annotation (default)")
    annotate_p.add_argument("input", nargs="?", help="JSON observation file or -")
    annotate_p.add_argument("--observation-id", default="obs_cli")
    annotate_p.add_argument("--prompt-id", default="prompt_default")
    annotate_p.add_argument("--client-id", default="meaning-mapper-cli")
    annotate_p.add_argument("-o", "--output", help="Write JSON to path")

    hext_p = sub.add_parser("hext", help="Optional HEXT normalize via Core library")
    hext_p.add_argument("input", nargs="?", help="Input file or -")
    hext_p.add_argument("-t", "--type", dest="source_type")
    hext_p.add_argument("-o", "--output")

    parser.add_argument(
        "--version",
        action="version",
        version=f"meaning-mapper {__version__}",
    )
    # Backward-compatible positional: treat bare input as annotate
    parser.add_argument("input", nargs="?", help=argparse.SUPPRESS)
    parser.add_argument("-o", "--output", dest="legacy_output", help=argparse.SUPPRESS)
    return parser


def _read_json(path: str) -> dict[str, Any]:
    if path == "-":
        raw = sys.stdin.read()
    else:
        raw = Path(path).read_text(encoding="utf-8")
    data = json.loads(raw)
    if not isinstance(data, dict):
        raise TypeError("input must be a JSON object")
    return data


def _write(payload: str, output: str | None) -> None:
    if output:
        Path(output).write_text(payload, encoding="utf-8")
    else:
        sys.stdout.write(payload)


def _cmd_annotate(
    input_path: str,
    *,
    observation_id: str,
    prompt_id: str,
    client_id: str,
    output: str | None,
) -> int:
    raw = _read_json(input_path)
    # Allow wrapping SA005 request files or bare observational data.
    if "raw_observational_data" in raw:
        obs_id = str(raw.get("observation_id", observation_id))
        prompt = str(raw.get("prompt_id", prompt_id))
        client = str(raw.get("client_id", client_id))
        data = dict(raw["raw_observational_data"])
    else:
        obs_id, prompt, client, data = observation_id, prompt_id, client_id, raw

    engine = DeterministicAnnotatorEngine()
    wire = engine.annotate(
        observation_id=obs_id,
        prompt_id=prompt,
        raw_observational_data=data,
        client_id=client,
    )
    view = StandardRuntimeBridge().bridge_annotation(wire)
    _write(json.dumps(view.to_wire(), ensure_ascii=False, indent=2) + "\n", output)
    return 0


def _cmd_hext(input_path: str, source_type: str | None, output: str | None) -> int:
    from semantic_annotator.pipeline import annotate
    from validation import ValidationError

    if input_path == "-":
        raw_bytes = sys.stdin.buffer.read()
        filename = None
        source_ref = "stdin://"
    else:
        path = Path(input_path)
        raw_bytes = path.read_bytes()
        filename = path.name
        source_ref = path.resolve().as_uri()
    try:
        obj = annotate(
            raw_bytes,
            source_type=source_type,
            source_ref=source_ref,
            filename=filename,
        )
    except (OSError, ValidationError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    _write(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", output)
    return 0


def _run(argv: list[str] | None, prog: str) -> int:
    parser = build_parser(prog=prog)
    args = parser.parse_args(argv)

    if args.command == "hext":
        if not args.input:
            parser.error("hext requires input")
        return _cmd_hext(args.input, args.source_type, args.output)

    input_path = None
    output = None
    observation_id = "obs_cli"
    prompt_id = "prompt_default"
    client_id = "meaning-mapper-cli"

    if args.command == "annotate":
        input_path = args.input
        output = args.output
        observation_id = args.observation_id
        prompt_id = args.prompt_id
        client_id = args.client_id
    elif getattr(args, "input", None):
        input_path = args.input
        output = args.legacy_output

    if not input_path:
        parser.print_help()
        return 2

    try:
        return _cmd_annotate(
            input_path,
            observation_id=observation_id,
            prompt_id=prompt_id,
            client_id=client_id,
            output=output,
        )
    except (OSError, TypeError, ValueError, json.JSONDecodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


def main(argv: list[str] | None = None) -> int:
    return _run(argv, prog="meaning-mapper")


def main_compat(argv: list[str] | None = None) -> int:
    warnings.warn(
        "The 'semantic-annotator' CLI entry point is deprecated. Use 'meaning-mapper'.",
        DeprecationWarning,
        stacklevel=2,
    )
    return _run(argv, prog="semantic-annotator")
