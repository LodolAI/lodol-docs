#!/usr/bin/env python3
"""Generate MDX documentation for Lodol provider actions.

Parses provider.py files using Python AST (no external dependencies needed)
and generates MDX documentation files for the Fumadocs site.

Usage:
    python scripts/generate-actions-docs.py
"""

import ast
import json
import os
from pathlib import Path
from typing import Any


# ---------------------------------------------------------------------------
# Paths – relative to script location so it works from the docs project root
# ---------------------------------------------------------------------------
SCRIPT_DIR = Path(__file__).resolve().parent
DOCS_ROOT = SCRIPT_DIR.parent
SERVER_ROOT = DOCS_ROOT.parent / "server"
PROVIDERS_DIR = SERVER_ROOT / "src" / "skipflow" / "integrations" / "providers"
OUTPUT_DIR = DOCS_ROOT / "content" / "docs" / "api-reference" / "actions"

# ---------------------------------------------------------------------------
# Target providers: all providers with triggers + specifically requested ones
# ---------------------------------------------------------------------------
TRIGGER_PROVIDERS = [
    "airparser", "airtable", "box", "calendly", "canva", "clickup",
    "coda", "discord", "dropbox", "eventbrite", "gmail", "google_calendar",
    "google_docs", "google_drive", "google_sheets", "linear", "notion",
    "paypal", "slack", "stripe", "telegram", "todoist", "trello", "twitter",
]

ADDITIONAL_PROVIDERS = [
    "anthropic", "whatsapp", "openai", "google_translate", "youtube",
]

TARGET_PROVIDERS = sorted(set(TRIGGER_PROVIDERS + ADDITIONAL_PROVIDERS))

# ---------------------------------------------------------------------------
# ParameterType enum → display string
# ---------------------------------------------------------------------------
PARAM_TYPE_MAP = {
    "STRING": "string",
    "NUMBER": "number",
    "BOOLEAN": "boolean",
    "OBJECT": "object",
    "ARRAY": "array",
}


# ===================================================================
# AST helpers – recursively extract Python values from AST nodes
# ===================================================================

def _extract(node: ast.expr) -> Any:
    """Recursively extract a plain Python value from an AST expression."""
    if node is None:
        return None

    # Constant literals (str, int, float, bool, None)
    if isinstance(node, ast.Constant):
        return node.value

    # Name references (True, False, None, or enum identifiers)
    if isinstance(node, ast.Name):
        if node.id in ("True", "False", "None"):
            return {"True": True, "False": False, "None": None}[node.id]
        return node.id

    # NameConstant (Python <3.8 compat)
    if isinstance(node, ast.NameConstant):
        return node.value

    # Attribute access (e.g. ParameterType.STRING, actions.handler)
    if isinstance(node, ast.Attribute):
        if isinstance(node.value, ast.Name):
            return f"{node.value.id}.{node.attr}"
        return node.attr

    # Dict literal
    if isinstance(node, ast.Dict):
        result = {}
        for k, v in zip(node.keys, node.values):
            if k is not None:
                result[_extract(k)] = _extract(v)
        return result

    # List literal
    if isinstance(node, ast.List):
        return [_extract(el) for el in node.elts]

    # Tuple literal
    if isinstance(node, ast.Tuple):
        return tuple(_extract(el) for el in node.elts)

    # Set literal
    if isinstance(node, ast.Set):
        return {_extract(el) for el in node.elts}

    # Call – extract keyword arguments (used for ActionSpec, ParameterSpec, etc.)
    if isinstance(node, ast.Call):
        kwargs: dict[str, Any] = {}
        for kw in node.keywords:
            if kw.arg is not None:
                kwargs[kw.arg] = _extract(kw.value)
        # Also capture positional args for simple cases
        if node.args:
            kwargs["__args__"] = [_extract(a) for a in node.args]
        return kwargs

    # Unary operators (e.g. -1)
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
        val = _extract(node.operand)
        if isinstance(val, (int, float)):
            return -val

    # f-strings
    if isinstance(node, ast.JoinedStr):
        parts = []
        for v in node.values:
            if isinstance(v, ast.Constant):
                parts.append(str(v.value))
            else:
                parts.append("{...}")
        return "".join(parts)

    # staticmethod(...) or similar wrapper
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
        if node.args:
            return _extract(node.args[0])

    return None


# ===================================================================
# Provider parsing
# ===================================================================

def parse_provider(provider_id: str) -> dict[str, Any] | None:
    """Parse a provider.py file using AST and extract action specs."""
    provider_path = PROVIDERS_DIR / provider_id / "provider.py"
    if not provider_path.exists():
        return None

    source = provider_path.read_text(encoding="utf-8")
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return None

    info: dict[str, Any] = {
        "id": provider_id,
        "display_name": "",
        "description": "",
        "actions": {},
    }

    for node in ast.walk(tree):
        if not isinstance(node, ast.ClassDef):
            continue
        if not node.name.endswith("Provider"):
            continue

        for item in node.body:
            # Handle annotated assignments:  display_name: str = "Notion"
            if isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name):
                name = item.target.id
                if item.value is None:
                    continue
                val = _extract(item.value)

                if name == "display_name" and isinstance(val, str):
                    info["display_name"] = val
                elif name == "description" and isinstance(val, str):
                    info["description"] = val
                elif name == "action_specs" and isinstance(val, dict):
                    info["actions"] = val

            # Handle plain assignments:  display_name = "Notion"
            if isinstance(item, ast.Assign):
                for target in item.targets:
                    if isinstance(target, ast.Name):
                        name = target.id
                        val = _extract(item.value)
                        if name == "display_name" and isinstance(val, str):
                            info["display_name"] = val
                        elif name == "description" and isinstance(val, str):
                            info["description"] = val
                        elif name == "action_specs" and isinstance(val, dict):
                            info["actions"] = val
        break  # only process the first *Provider class

    if not info["display_name"]:
        info["display_name"] = provider_id.replace("_", " ").title()

    return info if info["actions"] else None


# ===================================================================
# Slug helpers
# ===================================================================

def provider_id_to_slug(pid: str) -> str:
    return pid.replace("_", "-")


# ===================================================================
# MDX generation
# ===================================================================

def _param_type(raw: Any) -> str:
    """Convert a ParameterType enum reference to a readable string."""
    if isinstance(raw, str):
        part = raw.split(".")[-1]
        return PARAM_TYPE_MAP.get(part, part.lower())
    return "string"


def _json_body_example(params: list[dict]) -> dict[str, Any]:
    """Build a representative JSON body from required params."""
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


def _mock_from_returns(returns: Any) -> Any:
    """Synthesise a plausible mock response from a JSON Schema ``returns``."""
    if not isinstance(returns, dict):
        return {"status": "success"}

    rtype = returns.get("type")

    # Void / null actions → simple success
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


def _schema_example(schema: dict) -> Any:
    """Return a single example value for a leaf JSON Schema node."""
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


def _mock_to_json(mock: Any) -> str:
    """Serialise a mock response to pretty JSON, handling edge cases."""
    if mock is None:
        return '{\n  "status": "success"\n}'
    try:
        # Convert tuples to lists for JSON serialisation
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


def generate_action_section(action_name: str, action: dict) -> str:
    """Return MDX for one action."""
    display = action.get("display_name", action_name.replace("_", " ").title())
    desc = action.get("description", "")
    path = action.get("path", f"/actions/library/unknown/{action_name}")
    method = action.get("method", "POST")
    raw_params = action.get("parameters", ())
    mock = action.get("mock_response")

    lines: list[str] = []

    # Header + endpoint
    lines.append(f"### {display}")
    lines.append("")
    lines.append(f"```\n{method} {path}\n```")
    lines.append("")
    lines.append(desc)
    lines.append("")

    # Params table
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
            pdesc = p.get("description", "")
            lines.append(f"| `{pname}` | {ptype} | {req} | {pdesc} |")
        lines.append("")

    # Curl example
    body = _json_body_example(param_list)
    body_json = json.dumps(body, indent=4)
    lines.append("**Example**")
    lines.append("")
    lines.append("```bash")
    lines.append(f"curl -X POST https://api.skipflow.com/v1{path} \\")
    lines.append('  -H "Authorization: Bearer sk_live_your_api_key" \\')
    lines.append('  -H "Content-Type: application/json" \\')
    lines.append(f"  -d '{body_json}'")
    lines.append("```")
    lines.append("")

    # Response – always include a Response section for consistency.
    # Use mock_response when present; otherwise synthesise from returns schema.
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
    """Return full MDX file content for one provider."""
    display = provider["display_name"]
    desc = provider["description"]

    parts: list[str] = []
    parts.append(f"---")
    parts.append(f"title: {display}")
    parts.append(f"description: API actions for the {display} integration.")
    parts.append(f"---")
    parts.append("")
    parts.append(f"## {display}")
    parts.append("")
    parts.append(desc)
    parts.append("")

    for action_name, action_data in provider["actions"].items():
        if not isinstance(action_data, dict):
            continue
        parts.append("---")
        parts.append("")
        parts.append(generate_action_section(action_name, action_data))

    return "\n".join(parts) + "\n"


def generate_index_mdx(providers: list[dict]) -> str:
    """Return the actions index page content."""
    cards: list[str] = []
    for p in sorted(providers, key=lambda x: x["display_name"]):
        slug = provider_id_to_slug(p["id"])
        name = p["display_name"]
        count = len([a for a in p["actions"].values() if isinstance(a, dict)])
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
        "description: API endpoints for executing provider actions in your workflows.",
        "---",
        "",
        "## Actions",
        "",
        "Actions are the building blocks of Lodol workflows. Each action connects to a third-party service and performs a specific operation — sending a message, creating a record, translating text, querying data, and more.",
        "",
        "Use the Lodol API to call actions directly and build powerful automated workflows.",
        "",
        "### Endpoint Format",
        "",
        "All action endpoints follow the same pattern:",
        "",
        "```",
        "POST /v1/actions/library/{provider}/{action}",
        "```",
        "",
        "### Request Format",
        "",
        "All action requests must include:",
        "",
        "- `Authorization` header with your API key",
        "- `Content-Type: application/json`",
        "- Action-specific parameters in the JSON body",
        "",
        "```bash",
        "curl -X POST https://api.skipflow.com/v1/actions/library/slack/send-message \\",
        '  -H "Authorization: Bearer sk_live_your_api_key" \\',
        '  -H "Content-Type: application/json" \\',
        "  -d '{",
        '    \"channel_id\": \"C123456\",',
        '    \"text\": \"Hello from Lodol!\"',
        "  }'",
        "```",
        "",
        "### Response Format",
        "",
        'All action responses return JSON. Successful responses typically include a `status` field set to `"success"` along with action-specific data.',
        "",
        "```json",
        "{",
        '  "status": "success",',
        '  "channel": "C123456",',
        '  "ts": "1705312200.000100"',
        "}",
        "```",
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
    """Return meta.json content for the actions directory."""
    pages = ["index"]
    for p in sorted(providers, key=lambda x: x["display_name"]):
        pages.append(provider_id_to_slug(p["id"]))

    return json.dumps({"title": "Actions", "pages": pages}, indent=2) + "\n"


# ===================================================================
# Main
# ===================================================================

def main() -> None:
    print(f"Generating actions documentation...")
    print(f"  Providers dir : {PROVIDERS_DIR}")
    print(f"  Output dir    : {OUTPUT_DIR}")
    print(f"  Targets       : {len(TARGET_PROVIDERS)}")
    print()

    providers: list[dict] = []
    for pid in TARGET_PROVIDERS:
        info = parse_provider(pid)
        if info:
            action_count = len([a for a in info["actions"].values() if isinstance(a, dict)])
            providers.append(info)
            print(f"  {pid:25s} -> {info['display_name']:25s} ({action_count} actions)")
        else:
            print(f"  {pid:25s} -> SKIPPED")

    print(f"\n  Total: {len(providers)} providers")

    # Ensure output dir exists
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Write meta.json
    (OUTPUT_DIR / "meta.json").write_text(generate_meta_json(providers))
    print(f"\n  Written: meta.json")

    # Write index.mdx
    (OUTPUT_DIR / "index.mdx").write_text(generate_index_mdx(providers))
    print(f"  Written: index.mdx")

    # Write per-provider files
    for p in providers:
        slug = provider_id_to_slug(p["id"])
        fname = f"{slug}.mdx"
        (OUTPUT_DIR / fname).write_text(generate_provider_mdx(p))
        print(f"  Written: {fname}")

    print(f"\n  Done! {len(providers) + 2} files generated in {OUTPUT_DIR.relative_to(DOCS_ROOT)}")


if __name__ == "__main__":
    main()
