#!/usr/bin/env python3
"""Refresh ``data/directory.json``: the directory's category groups and the
order of popularity.

Everything about an app, its logo, categories and triggers, comes with its
spec in ``data/actions/``. What belongs to the directory as a whole is
lodol.com's: its integrations directory groups the categories into the
sections it filters by, and lists the apps most popular first. This copies
both from the directory's data module, which is read as text, never run.

Usage::

    python scripts/refresh-directory.py
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.request
from pathlib import Path
from typing import Any, Callable


SCRIPT_DIR = Path(__file__).resolve().parent
DOCS_ROOT = SCRIPT_DIR.parent
ACTIONS_DIR = DOCS_ROOT / "data" / "actions"
OUTPUT = DOCS_ROOT / "data" / "directory.json"

SITE = "https://www.lodol.com"

#: Lodol's own steps. lodol.com lists some of them as apps; the docs give
#: them a section of their own.
BUILT_IN_PREFIX = "skipflow_"

ABOUT = (
    "The integrations directory's category groups and its apps in order of "
    "popularity, copied from lodol.com by scripts/refresh-directory.py."
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
            "changed; update the patterns in scripts/refresh-directory.py."
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
            "patterns in scripts/refresh-directory.py."
        )
    popular = _POPULAR_RE.search(js)
    return groups, apps, popular.group(1).split(".") if popular else []


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
# Refresh
# ---------------------------------------------------------------------------

def build(
    groups: list[dict], site_apps: list[dict], popular: list[str], providers: dict[str, str]
) -> dict[str, Any]:
    pid_by_slug = {app["slug"]: pid for pid, app in match_apps(site_apps, providers).items()}
    return {
        "about": ABOUT,
        "groups": groups,
        "popular": [pid_by_slug[slug] for slug in popular if slug in pid_by_slug],
    }


def refresh(get: Fetch, providers: dict[str, str]) -> dict[str, Any]:
    groups, site_apps, popular = parse_catalog(catalog_module(get))
    return build(groups, site_apps, popular, providers)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", "-o", type=Path, default=OUTPUT)
    args = parser.parse_args(argv)

    print("Refreshing the directory's groups and popularity from lodol.com...")
    data = refresh(fetch, load_providers(ACTIONS_DIR))
    args.output.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"  Groups       : {len(data['groups'])}")
    print(f"  Popular apps : {len(data['popular'])}")
    print(f"  Wrote {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
