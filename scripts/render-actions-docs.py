#!/usr/bin/env python3
"""Render the per-provider Actions API reference from ``data/actions.json``.

This is the docs-side renderer. It consumes the JSON artifact published
by the server repo (``lodolai/lodol``) — see
``projects/server/scripts/extract_action_specs.py`` over there — and
writes one MDX page per provider plus an index and a ``meta.json``.

The renderer has no knowledge of Python AST or of any server source:
its sole input is the JSON file. This keeps the docs repo
self-contained and lets local docs builds work without cloning any
private server code.

Usage::

    python scripts/render-actions-docs.py
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent
DOCS_ROOT = SCRIPT_DIR.parent
DEFAULT_INPUT = DOCS_ROOT / "data" / "actions.json"
DEFAULT_OUTPUT_DIR = DOCS_ROOT / "content" / "docs" / "api-reference" / "actions"


PARAM_TYPE_MAP = {
    "STRING": "string",
    "NUMBER": "number",
    "BOOLEAN": "boolean",
    "OBJECT": "object",
    "ARRAY": "array",
}


# ---------------------------------------------------------------------------
# Slug helpers
# ---------------------------------------------------------------------------

def provider_id_to_slug(pid: str) -> str:
    return pid.replace("_", "-")


# ---------------------------------------------------------------------------
# MDX generation
# ---------------------------------------------------------------------------

def _param_type(raw: Any) -> str:
    if isinstance(raw, str):
        part = raw.split(".")[-1]
        return PARAM_TYPE_MAP.get(part, part.lower())
    return "string"


def _json_body_example(params: list[dict]) -> dict[str, Any]:
    body: dict[str, Any] = {}
    for p in params:
        if not isinstance(p, dict):
            continue
        if not p.get("required", False):
            continue
        name = p.get("name", "param")
        ptype = _param_type(p.get("type", "string"))
        if ptype == "string":
            body[name] = f"your_{name}"
        elif ptype == "number":
            body[name] = 10
        elif ptype == "boolean":
            body[name] = True
        elif ptype == "object":
            body[name] = {}
        elif ptype == "array":
            body[name] = []
    return body


def _schema_example(schema: dict) -> Any:
    t = schema.get("type", "string")
    if t == "string":
        return "example_value"
    if t == "number" or t == "integer":
        return 1
    if t == "boolean":
        return True
    if t == "array":
        return []
    if t == "object":
        props = schema.get("properties")
        if isinstance(props, dict):
            return {k: _schema_example(v) for k, v in props.items() if isinstance(v, dict)}
        return {}
    return None


def _mock_from_returns(returns: Any) -> Any:
    if not isinstance(returns, dict):
        return {"status": "success"}

    rtype = returns.get("type")

    if rtype in ("null", None):
        return {"status": "success"}

    if rtype == "string":
        return "example_value"

    if rtype == "number":
        return 1

    if rtype == "boolean":
        return True

    if rtype == "array":
        items = returns.get("items")
        if isinstance(items, dict):
            if items.get("type") == "string":
                return ["value_1", "value_2"]
            if items.get("type") == "object":
                child: dict[str, Any] = {}
                for k, v in (items.get("properties") or {}).items():
                    if isinstance(v, dict):
                        child[k] = _schema_example(v)
                return [child] if child else []
        return []

    if rtype == "object":
        obj: dict[str, Any] = {}
        props = returns.get("properties") or {}
        for k, v in props.items():
            if isinstance(v, dict):
                obj[k] = _schema_example(v)
        return obj if obj else {"status": "success"}

    return {"status": "success"}


def _mock_to_json(mock: Any) -> str:
    if mock is None:
        return '{\n  "status": "success"\n}'
    try:
        def _fixup(obj: Any) -> Any:
            if isinstance(obj, tuple):
                return list(obj)
            if isinstance(obj, dict):
                return {k: _fixup(v) for k, v in obj.items()}
            if isinstance(obj, list):
                return [_fixup(i) for i in obj]
            if isinstance(obj, set):
                return sorted(obj)
            return obj

        return json.dumps(_fixup(mock), indent=2)
    except (TypeError, ValueError):
        return json.dumps(str(mock))


def _escape_mdx(text: Any) -> str:
    """Escape characters MDX would otherwise interpret as JSX.

    ``{`` and ``}`` are treated as JSX expression delimiters; ``<``
    opens a JSX tag. Replace them with HTML entities so they render as
    literal characters in prose.
    """
    if text is None:
        return ""
    s = str(text)
    return (
        s.replace("{", "&#123;")
        .replace("}", "&#125;")
        .replace("<", "&lt;")
    )


def _escape_mdx_cell(text: Any) -> str:
    return (
        _escape_mdx(text)
        .replace("|", "\\|")
        .replace("\n", " ")
    )


def _yaml_quote(text: Any) -> str:
    s = "" if text is None else str(text)
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'


def generate_action_section(action_name: str, action: dict) -> str:
    display = action.get("display_name", action_name.replace("_", " ").title())
    desc = action.get("description", "")
    raw_params = action.get("parameters", [])
    mock = action.get("mock_response")

    lines: list[str] = []

    lines.append(f"### {_escape_mdx(display)}")
    lines.append("")
    lines.append(_escape_mdx(desc))
    lines.append("")

    param_list = list(raw_params) if isinstance(raw_params, (list, tuple)) else []
    param_list = [p for p in param_list if isinstance(p, dict)]
    if param_list:
        lines.append("**Parameters**")
        lines.append("")
        lines.append("| Parameter | Type | Required | Description |")
        lines.append("| --- | --- | --- | --- |")
        for p in param_list:
            pname = p.get("name", "")
            ptype = _param_type(p.get("type", "string"))
            req = "Yes" if p.get("required") else "No"
            pdesc = _escape_mdx_cell(p.get("description", ""))
            lines.append(f"| `{pname}` | {ptype} | {req} | {pdesc} |")
        lines.append("")

    returns = action.get("returns", {})
    if mock is not None:
        response_json = _mock_to_json(mock)
    else:
        response_json = _mock_to_json(_mock_from_returns(returns))

    lines.append("**Response**")
    lines.append("")
    lines.append(f"```json\n{response_json}\n```")
    lines.append("")

    return "\n".join(lines)


def generate_provider_mdx(provider: dict) -> str:
    display = provider["display_name"]
    desc = provider.get("description", "")

    parts: list[str] = []
    parts.append("---")
    parts.append(f"title: {_yaml_quote(display)}")
    parts.append(
        f"description: {_yaml_quote(f'API actions for the {display} integration.')}"
    )
    parts.append("---")
    parts.append("")
    parts.append(f"## {_escape_mdx(display)}")
    parts.append("")
    parts.append(_escape_mdx(desc))
    parts.append("")

    for action_name, action_data in provider.get("actions", {}).items():
        if not isinstance(action_data, dict):
            continue
        parts.append("---")
        parts.append("")
        parts.append(generate_action_section(action_name, action_data))

    return "\n".join(parts) + "\n"


def generate_index_mdx(providers: list[dict]) -> str:
    cards: list[str] = []
    for p in sorted(providers, key=lambda x: x["display_name"]):
        slug = provider_id_to_slug(p["id"])
        name = p["display_name"]
        count = len(
            [a for a in p.get("actions", {}).values() if isinstance(a, dict)]
        )
        desc_str = f"{count} action{'s' if count != 1 else ''} available"
        cards.append(
            f'  <Card\n'
            f'    title="{name}"\n'
            f'    description="{desc_str}"\n'
            f'    href="/docs/api-reference/actions/{slug}"\n'
            f'  />'
        )

    cards_block = "\n".join(cards)

    lines = [
        "---",
        "title: Actions",
        "description: Browse available integrations and their actions.",
        "---",
        "",
        "## Actions",
        "",
        "Actions are the building blocks of Lodol workflows. Each action connects to a third-party service and performs a specific operation — sending a message, creating a record, translating text, querying data, and more.",
        "",
        "### Available Providers",
        "",
        "<Cards>",
        cards_block,
        "</Cards>",
        "",
    ]
    return "\n".join(lines)


def generate_meta_json(providers: list[dict]) -> str:
    pages = ["index"]
    for p in sorted(providers, key=lambda x: x["display_name"]):
        pages.append(provider_id_to_slug(p["id"]))
    return json.dumps({"title": "Actions", "pages": pages}, indent=2) + "\n"


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def load_specs(input_path: Path) -> list[dict[str, Any]]:
    """Load the providers list from the input JSON file.

    Returns an empty list (with a warning) if the file is missing so a
    fresh checkout of the docs repo still produces a buildable site —
    the per-provider pages will simply not exist until the next run of
    the server-side ``publish-action-specs`` workflow lands an update.
    """
    if not input_path.exists():
        print(
            f"warning: {input_path} not found; no action docs will be generated. "
            "The file is published by lodolai/lodol's "
            "publish-action-specs workflow.",
            file=sys.stderr,
        )
        return []

    payload = json.loads(input_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or "providers" not in payload:
        print(
            f"warning: {input_path} has unexpected shape; expected a dict "
            "with a 'providers' key.",
            file=sys.stderr,
        )
        return []
    return [p for p in payload["providers"] if isinstance(p, dict)]


def render(providers: list[dict], output_dir: Path) -> None:
    """Render all MDX outputs into ``output_dir``."""
    if output_dir.exists():
        for existing in output_dir.iterdir():
            if existing.is_file():
                existing.unlink()
    output_dir.mkdir(parents=True, exist_ok=True)

    (output_dir / "meta.json").write_text(generate_meta_json(providers))
    (output_dir / "index.mdx").write_text(generate_index_mdx(providers))
    for p in providers:
        slug = provider_id_to_slug(p["id"])
        (output_dir / f"{slug}.mdx").write_text(generate_provider_mdx(p))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--input",
        "-i",
        type=Path,
        default=DEFAULT_INPUT,
        help="Path to actions.json (default: data/actions.json).",
    )
    parser.add_argument(
        "--output-dir",
        "-o",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="Where to write the MDX files.",
    )
    args = parser.parse_args(argv)

    providers = load_specs(args.input)
    print(f"Rendering actions docs...")
    print(f"  Input        : {args.input}")
    print(f"  Output dir   : {args.output_dir}")
    print(f"  Providers    : {len(providers)}")

    render(providers, args.output_dir)

    print(f"  Done! {len(providers) + 2} files written.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
