#!/usr/bin/env python3
"""Render the per-provider Actions API reference from ``data/actions/``.

This is the docs-side renderer. It consumes the JSON artifact published
by the server repo (``lodolai/lodol``) — see
``projects/server/scripts/extract_action_specs.py`` over there — and
writes one MDX page per provider plus an index and a ``meta.json``.
The artifact is one file per provider, ``data/actions/<provider id>.json``,
so that no single file approaches GitHub's 100 MB limit.

The renderer has no knowledge of Python AST or of any server source:
its sole input is those JSON files. This keeps the docs repo
self-contained and lets local docs builds work without cloning any
private server code.

Usage::

    python scripts/render-actions-docs.py
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent
DOCS_ROOT = SCRIPT_DIR.parent
DEFAULT_INPUT = DOCS_ROOT / "data" / "actions"
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

    if rtype in ("number", "integer"):
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


def _returns_example(returns: Any) -> Any:
    """An example of the output ``returns`` describes: the first example the
    schema lists, else one made up from its type."""
    if isinstance(returns, dict):
        examples = returns.get("examples")
        if isinstance(examples, list) and examples:
            return examples[0]
    return _mock_from_returns(returns)


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


# Text Markdown shows as written (a backslash escape, or a code span: a run
# of backticks closed by a run of the same length), or else an image opener.
_LITERAL_OR_IMAGE_RE = re.compile(r"\\.|(?<!`)(`+)(?!`).*?(?<!`)\1(?!`)|!\[")


def _escape_mdx(text: Any) -> str:
    """Escape characters MDX would otherwise interpret as JSX or an image.

    ``{`` and ``}`` are treated as JSX expression delimiters; ``<``
    opens a JSX tag. Replace them with HTML entities so they render as
    literal characters in prose.

    ``![`` opens an image, and fumadocs turns an image whose source isn't
    a web URL into an ``import`` of that file, so Slack's ``![](@U123)``
    mention syntax failed the build. Escape the bracket everywhere but in
    code spans, which already show their text as written.
    """
    if text is None:
        return ""
    s = (
        str(text)
        .replace("{", "&#123;")
        .replace("}", "&#125;")
        .replace("<", "&lt;")
    )
    return _LITERAL_OR_IMAGE_RE.sub(
        lambda m: "!\\[" if m.group(0) == "![" else m.group(0), s
    )


def _escape_mdx_cell(text: Any) -> str:
    return (
        _escape_mdx(text)
        .replace("|", "\\|")
        .replace("\n", " ")
    )


#: A parameter's choices are listed in full up to this many; a longer list
#: shows its first ``CHOICES_SHOWN`` and says how many more there are.
CHOICES_LISTED_IN_FULL = 12
CHOICES_SHOWN = 10


def _code_span(text: str) -> str:
    """``text`` as inline code that holds together in an MDX table cell.

    MDX shows code as written, so braces and ``<`` need no escaping (an
    HTML entity would show as written too). A pipe still ends the cell
    unless escaped, and a backtick in ``text`` needs a longer fence.
    """
    text = text.replace("\n", " ")
    longest_run = max((len(run) for run in re.findall("`+", text)), default=0)
    fence = "`" * (longest_run + 1)
    if text.startswith("`") or text.endswith("`"):
        text = f" {text} "
    return f"{fence}{text}{fence}".replace("|", "\\|")


def _value_code(value: Any) -> str:
    """A value as a caller sends it: text as it is, anything else as JSON."""
    if isinstance(value, str) and value.strip():
        return _code_span(value)
    return _code_span(json.dumps(value))


def _number(value: Any) -> str | None:
    """``value`` written out if it is a number, else None."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return json.dumps(value)


def _choice(option: dict) -> str:
    """One allowed value, followed by its label when the label says more."""
    value = option["value"]
    text = _value_code(value)
    label = str(option.get("label") or "").strip()
    if label and label.casefold() != str(value).strip().casefold():
        text += f" ({_escape_mdx_cell(label)})"
    return text


def _parameter_facts(param: dict) -> str:
    """The choices, range and default a parameter declares, as sentences."""
    facts: list[str] = []

    options = [
        o for o in param.get("options") or [] if isinstance(o, dict) and "value" in o
    ]
    if options:
        shown = (
            options
            if len(options) <= CHOICES_LISTED_IN_FULL
            else options[:CHOICES_SHOWN]
        )
        choices = ", ".join(_choice(o) for o in shown)
        if len(shown) < len(options):
            choices += f", and {len(options) - len(shown)} more"
        several = param.get("multi_select") or _param_type(param.get("type")) == "array"
        facts.append(f"{'One or more of' if several else 'One of'}: {choices}.")

    low, high = _number(param.get("minimum")), _number(param.get("maximum"))
    if low is not None and high is not None:
        facts.append(f"From {low} to {high}.")
    elif low is not None:
        facts.append(f"At least {low}.")
    elif high is not None:
        facts.append(f"At most {high}.")

    if param.get("default") not in (None, "", [], {}):
        facts.append(f"Default: {_value_code(param['default'])}.")

    return " ".join(facts)


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
            facts = _parameter_facts(p)
            if facts:
                pdesc = f"{pdesc}<br />{facts}" if pdesc else facts
            lines.append(f"| `{pname}` | {ptype} | {req} | {pdesc} |")
        lines.append("")

    returns = action.get("returns", {})
    summary = returns.get("description") if isinstance(returns, dict) else None
    summary = summary.strip() if isinstance(summary, str) else ""
    no_output = (
        mock is None and isinstance(returns, dict) and returns.get("type") == "null"
    )

    lines.append("**Response**")
    lines.append("")
    if summary:
        lines.append(_escape_mdx(summary))
        lines.append("")
    if no_output:
        # Nothing to show an example of: say so, unless the summary already has.
        if not summary:
            lines.append("This action has no output.")
            lines.append("")
    else:
        example = mock if mock is not None else _returns_example(returns)
        lines.append(f"```json\n{_mock_to_json(example)}\n```")
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
    """Load the providers to render from ``input_path``.

    ``input_path`` is normally ``data/actions/``, a directory holding one
    JSON file per provider. A single JSON file with a ``providers`` list,
    which the server's extractor writes when given ``--output``, is read
    too.

    Returns an empty list (with a warning) if the input is missing so a
    fresh checkout of the docs repo still produces a buildable site —
    the per-provider pages will simply not exist until the next run of
    the server-side ``publish-action-specs`` workflow lands an update.
    """
    if input_path.is_dir():
        return _load_spec_files(input_path)

    if not input_path.exists():
        print(
            f"warning: {input_path} not found; no action docs will be generated. "
            "The specs are published by lodolai/lodol's "
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


def _load_spec_files(directory: Path) -> list[dict[str, Any]]:
    """Read each ``<provider id>.json`` in ``directory``, in file-name order."""
    paths = sorted(directory.glob("*.json"))
    if not paths:
        print(
            f"warning: {directory} holds no provider files; "
            "no action docs will be generated.",
            file=sys.stderr,
        )
    providers: list[dict[str, Any]] = []
    for path in paths:
        provider = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(provider, dict):
            print(
                f"warning: {path} is not a provider object; skipped.",
                file=sys.stderr,
            )
            continue
        providers.append(provider)
    return providers


def render(providers: list[dict], output_dir: Path) -> None:
    """Render all MDX outputs into ``output_dir``."""
    if output_dir.exists():
        for existing in output_dir.iterdir():
            if existing.is_file():
                existing.unlink()
    output_dir.mkdir(parents=True, exist_ok=True)

    (output_dir / "meta.json").write_text(
        generate_meta_json(providers),
        encoding="utf-8",
    )
    (output_dir / "index.mdx").write_text(
        generate_index_mdx(providers),
        encoding="utf-8",
    )
    for p in providers:
        slug = provider_id_to_slug(p["id"])
        (output_dir / f"{slug}.mdx").write_text(
            generate_provider_mdx(p),
            encoding="utf-8",
        )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--input",
        "-i",
        type=Path,
        default=DEFAULT_INPUT,
        help="A directory of per-provider JSON files, or one JSON file with "
        'a "providers" list (default: data/actions).',
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
