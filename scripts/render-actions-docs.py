#!/usr/bin/env python3
"""Render the Integrations reference from ``data/actions/``.

This is the docs-side renderer. It consumes the JSON artifact published
by the server repo (``lodolai/lodol``) — see
``projects/server/scripts/extract_action_specs.py`` over there — and
writes the Integrations tab of the docs:

* one MDX page per app, at ``/docs/integrations/<app>``;
* one MDX page per built-in step group (If, Repeat, Approvals and the
  rest), at ``/docs/integrations/built-in/<name>``;
* the directory page, ``index.mdx``, and the ``meta.json`` files that
  order the sidebar;
* ``catalog.json``, the list the directory searches and the counts the
  home page shows.

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
import shutil
import sys
import unicodedata
from pathlib import Path
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent
DOCS_ROOT = SCRIPT_DIR.parent
DEFAULT_INPUT = DOCS_ROOT / "data" / "actions"
DEFAULT_OUTPUT_DIR = DOCS_ROOT / "content" / "docs" / "integrations"

#: Where the generated pages are served.
BASE_URL = "/docs/integrations"

#: Lodol's own steps are published as providers whose id starts with this.
BUILT_IN_PREFIX = "skipflow_"

#: The folder, under the output directory, that holds the built-in steps.
BUILT_IN_DIR = "built-in"


PARAM_TYPE_MAP = {
    "STRING": "string",
    "NUMBER": "number",
    "BOOLEAN": "boolean",
    "OBJECT": "object",
    "ARRAY": "array",
}

#: How each kind of value is named on the page: the words the editor uses
#: for a workflow's inputs, not a programming language's.
TYPE_LABELS = {
    "string": "text",
    "number": "number",
    "integer": "number",
    "boolean": "true/false",
    "object": "object",
    "array": "list",
    "date": "date",
    "datetime": "date and time",
    "time": "time",
}

#: An icon (a lucide-react name) for each built-in step group. A group the
#: server adds later falls back to DEFAULT_BUILT_IN_ICON.
BUILT_IN_ICONS = {
    "skipflow_agent": "Sparkles",
    "skipflow_code": "CodeXml",
    "skipflow_conditions": "Split",
    "skipflow_datetime": "CalendarClock",
    "skipflow_delay": "Hourglass",
    "skipflow_display": "Eye",
    "skipflow_http": "Globe",
    "skipflow_lists": "List",
    "skipflow_loops": "Repeat",
    "skipflow_math": "Calculator",
    "skipflow_random": "Dices",
    "skipflow_review": "UserCheck",
    "skipflow_schedule": "Clock",
    "skipflow_text": "Type",
    "skipflow_variables": "Database",
    "skipflow_workflows": "Workflow",
}
DEFAULT_BUILT_IN_ICON = "Box"

#: The hand-written guide that explains when and how to use a built-in step.
BUILT_IN_GUIDES = {
    "skipflow_agent": ("Use an AI agent", "/docs/guides/ai-agents"),
    "skipflow_code": ("Call an API or run code", "/docs/guides/http-and-code"),
    "skipflow_conditions": ("Make decisions", "/docs/guides/conditions"),
    "skipflow_http": ("Call an API or run code", "/docs/guides/http-and-code"),
    "skipflow_loops": ("Repeat steps", "/docs/guides/loops"),
    "skipflow_review": ("Ask for approval", "/docs/guides/approvals"),
    "skipflow_schedule": ("Triggers and schedules", "/docs/concepts/triggers"),
    "skipflow_variables": ("Remember values between runs", "/docs/guides/stored-values"),
    "skipflow_workflows": ("Run a workflow from another", "/docs/guides/sub-workflows"),
}

#: Apps the directory shows first, before the full A–Z list. Ids missing
#: from the catalog are skipped.
POPULAR_APPS = [
    "gmail",
    "slack",
    "google_sheets",
    "notion",
    "hubspot",
    "stripe",
    "salesforce",
    "airtable",
    "openai",
    "anthropic",
    "github",
    "jira",
    "shopify",
    "google_calendar",
    "microsoft_outlook",
    "quickbooks",
]

#: An app page lists its actions in a table at the top once it has this many.
OVERVIEW_MIN_ACTIONS = 3


# ---------------------------------------------------------------------------
# Providers
# ---------------------------------------------------------------------------

def provider_id_to_slug(pid: str) -> str:
    return pid.replace("_", "-")


def is_built_in(provider: dict) -> bool:
    return str(provider.get("id", "")).startswith(BUILT_IN_PREFIX)


def provider_path(provider: dict) -> str:
    """Where a provider's page lives, relative to the output directory and
    without the ``.mdx``: ``gmail``, or ``built-in/review`` for a step."""
    pid = str(provider["id"])
    if is_built_in(provider):
        return f"{BUILT_IN_DIR}/{provider_id_to_slug(pid[len(BUILT_IN_PREFIX):])}"
    return provider_id_to_slug(pid)


def provider_url(provider: dict) -> str:
    return f"{BASE_URL}/{provider_path(provider)}"


def _sort_key(provider: dict) -> str:
    return str(provider.get("display_name", "")).casefold()


def _actions(provider: dict) -> list[tuple[str, dict]]:
    return [
        (name, action)
        for name, action in (provider.get("actions") or {}).items()
        if isinstance(action, dict)
    ]


def _is_section_marker(action: dict) -> bool:
    """An "End if" or "End repeat" step: it closes the section an If or a
    Repeat opened, takes nothing and returns nothing, so it is described on
    the step that opens the section rather than as an action of its own."""
    return (
        action.get("handler") == "_control_flow"
        and not action.get("parameters")
        and str(action.get("display_name", "")).startswith("End ")
    )


def _action_name(action_name: str, action: dict) -> str:
    return _one_line(action.get("display_name", action_name.replace("_", " ").title()))


def visible_actions(provider: dict) -> list[tuple[str, dict]]:
    """A provider's actions in the order its page lists them: by name."""
    actions = [(n, a) for n, a in _actions(provider) if not _is_section_marker(a)]
    return sorted(actions, key=lambda item: _action_name(*item).casefold())


# ---------------------------------------------------------------------------
# Headings
# ---------------------------------------------------------------------------

def github_slug(text: str) -> str:
    """The anchor fumadocs gives a heading (``github-slugger``'s rule): lower
    case, with everything but letters, digits, marks, connector punctuation,
    spaces and hyphens removed, and each space turned into a hyphen."""
    kept = (
        ch
        for ch in text.lower()
        if ch in " -"
        or unicodedata.category(ch)[0] in "LMN"
        or unicodedata.category(ch) == "Pc"
    )
    return "".join(kept).replace(" ", "-")


class Slugger:
    """Hands out anchors as fumadocs does: a heading whose anchor is taken
    gets ``-1``, ``-2`` and so on, in the order the headings appear."""

    def __init__(self) -> None:
        self._seen: dict[str, int] = {}

    def slug(self, text: str) -> str:
        base = github_slug(text)
        result = base
        while result in self._seen:
            self._seen[base] += 1
            result = f"{base}-{self._seen[base]}"
        self._seen[result] = 0
        return result


# ---------------------------------------------------------------------------
# MDX helpers
# ---------------------------------------------------------------------------

def _param_type(raw: Any) -> str:
    if isinstance(raw, str):
        part = raw.split(".")[-1]
        return PARAM_TYPE_MAP.get(part, part.lower())
    return "string"


def _type_label(kind: Any) -> str:
    """``text``, ``number``, ``list``… for a parameter type or a JSON Schema
    type; an unknown kind is shown as it is."""
    if isinstance(kind, list):
        kinds = [k for k in kind if k != "null"]
        kind = kinds[0] if kinds else "null"
    if not isinstance(kind, str) or not kind:
        return ""
    key = _param_type(kind) if kind.startswith("ParameterType.") else kind.lower()
    return TYPE_LABELS.get(key, key)


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


def _one_line(text: Any) -> str:
    """``text`` with its whitespace runs, line breaks included, made single
    spaces: a JSX attribute and a table cell each hold one line."""
    return " ".join(str(text or "").split())


#: Characters a quoted JSX attribute can't hold as written: MDX would end
#: the value at a quote and decode ``&amp;``-style references.
_ATTR_UNSAFE_RE = re.compile(r'["&\\]')


def _jsx_attr(name: str, value: Any) -> str:
    """``name="value"``, or ``name={"value"}`` when the value holds a quote,
    an ampersand or a backslash, so it reaches the component exactly."""
    text = _one_line(value)
    if _ATTR_UNSAFE_RE.search(text):
        return f"{name}={{{json.dumps(text, ensure_ascii=False)}}}"
    return f'{name}="{text}"'


#: A parameter's choices are listed in full up to this many; a longer list
#: shows its first ``CHOICES_SHOWN`` and says how many more there are.
CHOICES_LISTED_IN_FULL = 12
CHOICES_SHOWN = 10


def _code_span(text: str) -> str:
    """``text`` as an inline code span, fenced with enough backticks to hold
    any it contains. The page shows it as code, exactly as written."""
    text = text.replace("\n", " ")
    longest_run = max((len(run) for run in re.findall("`+", text)), default=0)
    fence = "`" * (longest_run + 1)
    if text.startswith("`") or text.endswith("`"):
        text = f" {text} "
    return f"{fence}{text}{fence}"


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
    label = _one_line(option.get("label"))
    if label and label.casefold() != str(value).strip().casefold():
        text += f" ({label})"
    return text


def _parameter_facts(param: dict) -> str:
    """The choices, range and default a parameter declares, as sentences.

    Values are written as code spans, which the page shows as code; the rest
    is plain text, shown as written."""
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


# ---------------------------------------------------------------------------
# Pages
# ---------------------------------------------------------------------------

def _input_field(param: dict) -> str:
    """One input as a ``<Field>``: the label the editor shows, the name a
    workflow's JSON uses, its type, whether it is required, and what it is."""
    name = _one_line(param.get("name"))
    label = _one_line(param.get("display_name")) or name
    attrs = [_jsx_attr("name", label), _jsx_attr("id", name)]
    kind = _type_label(param.get("type", "ParameterType.STRING"))
    if kind:
        attrs.append(_jsx_attr("type", kind))
    if param.get("required"):
        attrs.append("required")
    description = _one_line(param.get("description"))
    if description:
        attrs.append(_jsx_attr("description", description))
    facts = _parameter_facts(param)
    if facts:
        attrs.append(_jsx_attr("facts", facts))
    return f"<Field {' '.join(attrs)} />"


def _output_field(key: str, schema: dict) -> str:
    attrs = [_jsx_attr("id", key)]
    kind = _type_label(schema.get("type"))
    if kind:
        attrs.append(_jsx_attr("type", kind))
    description = _one_line(schema.get("description"))
    if description:
        attrs.append(_jsx_attr("description", description))
    return f"<Field {' '.join(attrs)} />"


def _fields(attrs: list[str], fields: list[str]) -> list[str]:
    """A ``<Fields>`` list, self-closing when it has no fields to hold."""
    if not fields:
        return [f"<Fields {' '.join(attrs)} />", ""]
    return [f"<Fields {' '.join(attrs)}>", *fields, "</Fields>", ""]


def _returns_phrase(returns: dict) -> str:
    """What an action returns when its output has no fields to list."""
    kind = _type_label(returns.get("type"))
    if kind in ("", "object", "null"):
        return ""
    if kind == "text":
        return "Returns text."
    if kind == "true/false":
        return "Returns true or false."
    return f"Returns a {kind}."


def generate_action_section(action_name: str, action: dict) -> str:
    """An action's section: what it does, its inputs, its outputs and an
    example of what it returns."""
    display = action.get("display_name", action_name.replace("_", " ").title())
    desc = action.get("description", "")
    raw_params = action.get("parameters", [])
    mock = action.get("mock_response")

    lines: list[str] = [f"## {_escape_mdx(_one_line(display))}", ""]
    if desc:
        lines += [_escape_mdx(desc), ""]

    param_list = list(raw_params) if isinstance(raw_params, (list, tuple)) else []
    param_list = [p for p in param_list if isinstance(p, dict)]
    lines += _fields(['title="Inputs"'], [_input_field(p) for p in param_list])

    returns = action.get("returns", {})
    returns = returns if isinstance(returns, dict) else {}
    summary = returns.get("description")
    summary = _one_line(summary) if isinstance(summary, str) else ""
    no_output = mock is None and returns.get("type") == "null"
    props = returns.get("properties") if returns.get("type") == "object" else None
    outputs = [
        _output_field(key, schema)
        for key, schema in (props or {}).items()
        if isinstance(schema, dict)
    ]

    attrs = ['title="Outputs"']
    if not summary and no_output:
        summary = "This action has no output."
    elif not summary and not outputs:
        summary = _returns_phrase(returns)
    if summary:
        attrs.append(_jsx_attr("description", summary))
    lines += _fields(attrs, outputs)

    if not no_output:
        example = mock if mock is not None else _returns_example(returns)
        lines += [
            "<Example>",
            "",
            f"```json\n{_mock_to_json(example)}\n```",
            "",
            "</Example>",
            "",
        ]

    return "\n".join(lines)


def _action_overview(
    heading: str, column: str, rows: list[tuple[str, str, str]]
) -> list[str]:
    """The table of a page's actions, each linking to its section."""
    lines = [f"## {heading}", "", f"| {column} | What it does |", "| --- | --- |"]
    for display, anchor, desc in rows:
        name = _escape_mdx_cell(display)
        lines.append(f"| [{name}](#{anchor}) | {_escape_mdx_cell(_first_sentence(desc))} |")
    lines.append("")
    return lines


#: A full stop that ends one of these doesn't end the sentence: "e.g.",
#: "U.S.", or an initial such as "R.".
_ABBREVIATION_RE = re.compile(
    r"(?:\b(?:e\.g|i\.e|etc|vs|approx|incl|no|st|dr|mr|ms|jr)|(?<![\w.])[A-Z](?:\.[A-Z])*)\.$",
    re.IGNORECASE,
)


def _first_sentence(text: str) -> str:
    """The first sentence of ``text``, which is what an overview needs."""
    text = _one_line(text)
    for end in re.finditer(r"[.!?](?=\s|$)", text):
        sentence = text[: end.end()]
        if end.group() == "." and _ABBREVIATION_RE.search(sentence):
            continue
        return sentence
    return text


def generate_provider_mdx(provider: dict) -> str:
    display = _one_line(provider["display_name"])
    desc = _one_line(provider.get("description", ""))
    built_in = is_built_in(provider)
    actions = visible_actions(provider)

    parts: list[str] = ["---", f"title: {_yaml_quote(display)}"]
    parts.append(
        f"description: {_yaml_quote(desc or f'What {display} can do in a workflow.')}"
    )
    parts.append(f"integration: {'built-in' if built_in else 'app'}")
    parts.append(f"actions: {len(actions)}")
    if built_in:
        parts.append(
            f"icon: {BUILT_IN_ICONS.get(str(provider['id']), DEFAULT_BUILT_IN_ICON)}"
        )
    parts += ["---", ""]

    if built_in:
        guide = BUILT_IN_GUIDES.get(str(provider["id"]))
        if guide:
            parts += [
                f"To learn when to use these steps, with examples, read "
                f"[{guide[0]}]({guide[1]}).",
                "",
            ]
        markers = sorted(
            {
                _one_line(a.get("display_name"))
                for _, a in _actions(provider)
                if _is_section_marker(a)
            }
        )
        if markers:
            closers = " or ".join(f"**{_escape_mdx(m)}**" for m in markers)
            parts += [f"Close each section with an {closers} step.", ""]

    # Anchors are handed out in page order, as fumadocs does, so the action
    # list links to each section's heading.
    slugger = Slugger()
    heading, column = ("Steps", "Step") if built_in else ("Actions", "Action")
    show_overview = len(actions) >= OVERVIEW_MIN_ACTIONS
    if show_overview:
        slugger.slug(heading)
    sections: list[str] = []
    rows: list[tuple[str, str, str]] = []
    for action_name, action in actions:
        display_name = _action_name(action_name, action)
        rows.append(
            (display_name, slugger.slug(display_name), action.get("description", ""))
        )
        sections.append(generate_action_section(action_name, action))

    if show_overview:
        parts += _action_overview(heading, column, rows)
    parts += sections

    return "\n".join(parts).rstrip("\n") + "\n"


def generate_index_mdx(providers: list[dict]) -> str:
    """The directory page. ``IntegrationDirectory`` reads ``catalog.json``."""
    apps = [p for p in providers if not is_built_in(p)]
    lines = [
        "---",
        "title: Integrations",
        _yaml_line(
            "description",
            f"The {len(apps)} apps and the built-in steps a workflow can use, "
            "with every action's inputs and outputs.",
        ),
        "full: true",
        "---",
        "",
        "<IntegrationDirectory />",
        "",
    ]
    return "\n".join(lines)


def _yaml_line(key: str, value: str) -> str:
    return f"{key}: {_yaml_quote(value)}"


def generate_meta_json(providers: list[dict]) -> str:
    apps = sorted((p for p in providers if not is_built_in(p)), key=_sort_key)
    pages = ["index"]
    if any(is_built_in(p) for p in providers):
        pages += ["---Built-in steps---", f"...{BUILT_IN_DIR}"]
    pages.append("---Apps---")
    pages += [provider_path(p) for p in apps]
    meta = {
        "title": "Integrations",
        "description": "Apps and built-in steps",
        "root": True,
        "icon": "Blocks",
        "pages": pages,
    }
    return json.dumps(meta, indent=2) + "\n"


def generate_built_in_meta_json(providers: list[dict]) -> str:
    steps = sorted((p for p in providers if is_built_in(p)), key=_sort_key)
    pages = [provider_path(p).split("/", 1)[1] for p in steps]
    return json.dumps({"title": "Built-in steps", "pages": pages}, indent=2) + "\n"


def generate_catalog(providers: list[dict]) -> dict[str, Any]:
    """What the directory lists and searches, and the counts the home page
    shows."""
    entries = []
    for p in sorted(providers, key=_sort_key):
        built_in = is_built_in(p)
        entry: dict[str, Any] = {
            "id": p["id"],
            "name": _one_line(p["display_name"]),
            # A tile has room for a line or two; the page has the rest.
            "description": _first_sentence(p.get("description", "")),
            "href": provider_url(p),
            "actions": len(visible_actions(p)),
            "builtIn": built_in,
        }
        if built_in:
            entry["icon"] = BUILT_IN_ICONS.get(str(p["id"]), DEFAULT_BUILT_IN_ICON)
        entries.append(entry)
    ids = {p["id"] for p in providers if not is_built_in(p)}
    apps = [e for e in entries if not e["builtIn"]]
    return {
        "apps": len(apps),
        "appActions": sum(e["actions"] for e in apps),
        "popular": [pid for pid in POPULAR_APPS if pid in ids],
        "entries": entries,
    }


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


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def render(providers: list[dict], output_dir: Path) -> int:
    """Render every output into ``output_dir``, which is emptied first so a
    provider the server dropped leaves no page behind. Returns the number
    of files written."""
    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True)

    written = 0
    _write(output_dir / "meta.json", generate_meta_json(providers))
    _write(output_dir / "index.mdx", generate_index_mdx(providers))
    _write(
        output_dir / "catalog.json",
        json.dumps(generate_catalog(providers), ensure_ascii=False) + "\n",
    )
    written += 3
    if any(is_built_in(p) for p in providers):
        _write(
            output_dir / BUILT_IN_DIR / "meta.json",
            generate_built_in_meta_json(providers),
        )
        written += 1
    for p in providers:
        _write(output_dir / f"{provider_path(p)}.mdx", generate_provider_mdx(p))
        written += 1
    return written


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
    print("Rendering the integrations reference...")
    print(f"  Input        : {args.input}")
    print(f"  Output dir   : {args.output_dir}")
    print(f"  Providers    : {len(providers)}")

    written = render(providers, args.output_dir)

    print(f"  Done! {written} files written.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
