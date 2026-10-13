#!/usr/bin/env python3
"""Refresh ``data/apps.json``: each app's logo, categories and triggers.

The action specs in ``data/actions/`` don't carry them yet. Until the
server repo publishes them with the specs, they come from what Lodol
already publishes:

* lodol.com's integrations directory, whose data module lists every app
  with its logo and categories, the groups the categories belong to, and
  the apps in order of popularity;
* each app's page on lodol.com, which lists its triggers by name;
* Lodol's MCP server, for each trigger's filters and event fields: its
  ``search_triggers`` tool returns them. Save its results as JSON, either a
  list of triggers or ``{"<provider id>": [trigger, ...]}``, and pass the
  file with ``--trigger-details``. Details already in ``data/apps.json``
  are kept for every trigger lodol.com still lists.

lodol.com's pages are read as text, never run.

Usage::

    python scripts/refresh-app-data.py [--trigger-details FILE]
"""

from __future__ import annotations

import argparse
import concurrent.futures
import html
import json
import re
import sys
import urllib.request
from pathlib import Path
from typing import Any, Callable


SCRIPT_DIR = Path(__file__).resolve().parent
DOCS_ROOT = SCRIPT_DIR.parent
ACTIONS_DIR = DOCS_ROOT / "data" / "actions"
OUTPUT = DOCS_ROOT / "data" / "apps.json"

SITE = "https://www.lodol.com"

#: Lodol's own steps. lodol.com lists some of them as apps; the docs give
#: them a section of their own.
BUILT_IN_PREFIX = "skipflow_"

ABOUT = (
    "Logos, categories and triggers for the apps in data/actions, written by "
    "scripts/refresh-app-data.py. Apps, logos, categories and trigger names "
    "come from lodol.com; each trigger's filters and event fields from "
    "Lodol's MCP server."
)

Fetch = Callable[[str], str]


def fetch(url: str) -> str:
    request = urllib.request.Request(url, headers={"User-Agent": "lodol-docs"})
    with urllib.request.urlopen(request, timeout=60) as response:
        return response.read().decode("utf-8")


# ---------------------------------------------------------------------------
# lodol.com
# ---------------------------------------------------------------------------

_GROUP_RE = re.compile(r"\{key:`([^`]*)`,label:`([^`]*)`,categories:\[([^\]]*)\]\}")
_APP_RE = re.compile(
    r"\{slug:`([^`]*)`,name:`([^`]*)`,icon:`([^`]*)`"
    r"(?:,groups:\[[^\]]*\])?,categories:\[([^\]]*)\]\}"
)
#: The apps in order of popularity: one string of slugs joined by dots.
_POPULAR_RE = re.compile(r"`((?:[a-z0-9-]+\.){20,}[a-z0-9-]+)`")


def _find(pattern: str, text: str, what: str) -> str:
    match = re.search(pattern, text)
    if not match:
        raise SystemExit(
            f"error: couldn't find {what} on lodol.com. Its pages have "
            "changed; update the patterns in scripts/refresh-app-data.py."
        )
    return match.group(1)


def catalog_module(get: Fetch) -> str:
    """The integrations directory's data module, found through the page
    that loads it (its file names change with every deploy)."""
    page = get(f"{SITE}/integrations")
    component = _find(
        r'component-url="(/_astro/Integrations\.[^"]+\.js)"',
        page,
        "the directory's script",
    )
    module = _find(
        r'from"\./(integrations\.[\w-]+\.js)"',
        get(SITE + component),
        "the directory's data",
    )
    return get(f"{SITE}/_astro/{module}")


def _quoted(text: str) -> list[str]:
    return re.findall(r"`([^`]*)`", text)


def parse_catalog(js: str) -> tuple[list[dict], list[dict], list[str]]:
    """The category groups, the apps and the popularity order in the
    directory's data module."""
    groups = [
        {"key": key, "label": label, "categories": _quoted(categories)}
        for key, label, categories in _GROUP_RE.findall(js)
    ]
    apps = [
        {"slug": slug, "name": name, "icon": icon, "categories": _quoted(categories)}
        for slug, name, icon, categories in _APP_RE.findall(js)
    ]
    if not groups or not apps:
        raise SystemExit(
            "error: lodol.com's directory data has changed shape; update the "
            "patterns in scripts/refresh-app-data.py."
        )
    popular = _POPULAR_RE.search(js)
    return groups, apps, popular.group(1).split(".") if popular else []


def _text(fragment: str) -> str:
    return " ".join(html.unescape(re.sub(r"<[^>]+>", " ", fragment)).split())


def parse_triggers(page: str) -> list[dict]:
    """The triggers an app's page lists, by name and description, in order."""
    count = re.search(r"<strong>(\d+)</strong> triggers?<", page)
    section = re.search(r">Triggers</h2>(.*?)(?:<h2[ >]|</section>)", page, re.S)
    triggers = []
    if section:
        triggers = [
            {"display_name": _text(name), "description": _text(description)}
            for name, description in re.findall(
                r'class="_capName_[^"]*">(.*?)</span>\s*'
                r'<span class="_capDesc_[^"]*">(.*?)</span>',
                section.group(1),
                re.S,
            )
        ]
    if count and int(count.group(1)) != len(triggers):
        raise SystemExit(
            f"error: an app page on lodol.com says it has {count.group(1)} "
            f"triggers but {len(triggers)} were found; update the patterns in "
            "scripts/refresh-app-data.py."
        )
    return triggers


# ---------------------------------------------------------------------------
# Matching lodol.com's apps to the docs' providers
# ---------------------------------------------------------------------------

def load_providers(actions_dir: Path) -> dict[str, str]:
    """Each app's provider id and name in ``data/actions``. Built-in steps
    are left out."""
    providers = {}
    for path in sorted(actions_dir.glob("*.json")):
        spec = json.loads(path.read_text(encoding="utf-8"))
        pid = str(spec.get("id", path.stem))
        if not pid.startswith(BUILT_IN_PREFIX):
            providers[pid] = str(spec.get("display_name") or pid)
    return providers


def _name_key(name: str) -> str:
    return re.sub(r"[^a-z0-9]", "", name.casefold())


def match_apps(site_apps: list[dict], providers: dict[str, str]) -> dict[str, dict]:
    """lodol.com's app for each provider: the one with the same slug
    (``google_sheets`` is ``google-sheets``), else the one with the same
    name, ignoring case and punctuation (``monday`` is "Monday.com")."""
    by_slug = {app["slug"]: app for app in site_apps}
    by_name = {_name_key(app["name"]): app for app in site_apps}
    matched = {}
    for pid, name in providers.items():
        app = by_slug.get(pid.replace("_", "-")) or by_name.get(_name_key(name))
        if app:
            matched[pid] = app
    return matched


# ---------------------------------------------------------------------------
# Trigger details
# ---------------------------------------------------------------------------

def _owner(trigger_id: str, providers: set[str]) -> str | None:
    """The provider a trigger id belongs to: the longest id it starts with,
    so ``rackspace_email_admin_...`` isn't taken for ``rackspace_email``."""
    owners = [pid for pid in providers if trigger_id.startswith(pid + "_")]
    return max(owners, key=len) if owners else None


def index_details(payload: Any, providers: set[str]) -> dict[str, dict[str, dict]]:
    """Triggers with their filters and fields, by provider and then by name.
    ``payload`` is ``{provider id: [trigger, ...]}``, a plain list of
    triggers, or the ``apps`` of an earlier ``data/apps.json``."""
    known: dict[str, dict[str, dict]] = {}

    def add(pid: str | None, trigger: Any) -> None:
        if pid and isinstance(trigger, dict) and trigger.get("display_name"):
            known.setdefault(pid, {})[trigger["display_name"]] = trigger

    if isinstance(payload, list):
        for trigger in payload:
            if isinstance(trigger, dict):
                add(_owner(str(trigger.get("id", "")), providers), trigger)
    elif isinstance(payload, dict):
        for pid, value in payload.items():
            triggers = value.get("triggers") if isinstance(value, dict) else value
            for trigger in triggers or []:
                add(pid, trigger)
    return known


def merge_triggers(listed: list[dict], known: dict[str, dict]) -> list[dict]:
    """lodol.com's triggers, in its order, each with its details where they
    are known. A trigger with no details keeps its name and description."""
    merged = []
    for trigger in listed:
        detail = known.get(trigger["display_name"])
        if detail and (detail.get("params") is not None or detail.get("output") is not None):
            merged.append(detail)
        else:
            merged.append(trigger)
    return merged


# ---------------------------------------------------------------------------
# Refresh
# ---------------------------------------------------------------------------

def build(
    groups: list[dict],
    site_apps: list[dict],
    popular: list[str],
    triggers_by_slug: dict[str, list[dict]],
    providers: dict[str, str],
    known: dict[str, dict[str, dict]],
) -> dict[str, Any]:
    matched = match_apps(site_apps, providers)
    pid_by_slug = {app["slug"]: pid for pid, app in matched.items()}
    apps: dict[str, Any] = {}
    for pid in sorted(matched):
        app = matched[pid]
        icon = app["icon"]
        entry: dict[str, Any] = {
            "logo": SITE + icon if icon.startswith("/") else icon,
            "categories": app["categories"],
        }
        listed = triggers_by_slug.get(app["slug"]) or []
        if listed:
            entry["triggers"] = merge_triggers(listed, known.get(pid, {}))
        apps[pid] = entry
    return {
        "about": ABOUT,
        "groups": groups,
        "popular": [pid_by_slug[slug] for slug in popular if slug in pid_by_slug],
        "apps": apps,
    }


def refresh(
    get: Fetch,
    providers: dict[str, str],
    known: dict[str, dict[str, dict]],
    workers: int = 6,
) -> dict[str, Any]:
    groups, site_apps, popular = parse_catalog(catalog_module(get))
    slugs = [app["slug"] for app in match_apps(site_apps, providers).values()]
    with concurrent.futures.ThreadPoolExecutor(workers) as pool:
        pages = pool.map(lambda slug: get(f"{SITE}/integrations/{slug}"), slugs)
        triggers_by_slug = {slug: parse_triggers(page) for slug, page in zip(slugs, pages)}
    return build(groups, site_apps, popular, triggers_by_slug, providers, known)


def _summary(data: dict[str, Any], providers: dict[str, str]) -> list[str]:
    apps = data["apps"]
    triggers = [t for app in apps.values() for t in app.get("triggers", [])]
    bare = [t["display_name"] for t in triggers if "output" not in t]
    lines = [
        f"  Apps         : {len(apps)} of {len(providers)} matched on lodol.com",
        f"  Triggers     : {len(triggers)} in {sum(1 for a in apps.values() if a.get('triggers'))} apps",
    ]
    missing = sorted(set(providers) - set(apps))
    if missing:
        lines.append(f"  Not on lodol.com, so no logo or category: {', '.join(missing)}")
    if bare:
        lines.append(
            "  No filters or fields yet (get them from Lodol's MCP server and "
            f"pass --trigger-details): {', '.join(bare)}"
        )
    return lines


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--trigger-details",
        type=Path,
        help="JSON from Lodol's MCP server: triggers with their filters and fields.",
    )
    parser.add_argument("--output", "-o", type=Path, default=OUTPUT)
    args = parser.parse_args(argv)

    providers = load_providers(ACTIONS_DIR)
    known: dict[str, dict[str, dict]] = {}
    sources = [args.output] + ([args.trigger_details] if args.trigger_details else [])
    for source in sources:
        if source.exists():
            payload = json.loads(source.read_text(encoding="utf-8"))
            if source == args.output:
                payload = payload.get("apps", {})
            for pid, triggers in index_details(payload, set(providers)).items():
                known.setdefault(pid, {}).update(triggers)

    print("Refreshing app logos, categories and triggers from lodol.com...")
    data = refresh(fetch, providers, known)
    args.output.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print("\n".join(_summary(data, providers)))
    print(f"  Wrote {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
