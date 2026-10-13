"""Unit tests for ``scripts/refresh-directory.py``.

The script reads the category groups and the order of popularity from
lodol.com's integrations directory. These tests feed it small copies of
the directory's pages through a stub fetch, so they never touch the
network.
"""

from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve().parents[2] / "scripts" / "refresh-directory.py"


def _load_script():
    spec = importlib.util.spec_from_file_location("refresh_directory", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    sys.modules["refresh_directory"] = module
    spec.loader.exec_module(module)
    return module


ref = _load_script()

SITE = ref.SITE

MODULE = (
    "var e=[{key:`communication`,label:`Communication`,categories:[`Email`,`Messaging`]},"
    "{key:`app_families`,label:`App Families`,categories:[`Google`,`Lodol`]}],"
    "t=`gmail.slack.monday-com.code-by-lodol." + ".".join(f"filler-{i}" for i in range(20)) + "`,"
    "n=[{slug:`gmail`,name:`Gmail`,icon:`/app-icons/gmail-icon.png`,groups:[`communication`,`app_families`],"
    "categories:[`Email`,`Google`]},"
    "{slug:`slack`,name:`Slack`,icon:`/app-icons/slack-icon.webp`,categories:[`Messaging`]},"
    "{slug:`monday-com`,name:`Monday.com`,icon:`/app-icons/monday-com-icon.svg`,groups:[],categories:[]},"
    "{slug:`code-by-lodol`,name:`Code by Lodol`,icon:`/app-icons/code.svg`,groups:[`app_families`],"
    "categories:[`Lodol`]}];export{e as n,t as r,n as t};"
)

DIRECTORY = '<astro-island component-url="/_astro/Integrations.Ab12.js" props="{}"></astro-island>'
COMPONENT = 'import{a}from"./react.x.js";import{n,t}from"./integrations.Cd-34.js";'


PAGES = {
    f"{SITE}/integrations": DIRECTORY,
    f"{SITE}/_astro/Integrations.Ab12.js": COMPONENT,
    f"{SITE}/_astro/integrations.Cd-34.js": MODULE,
}

PROVIDERS = {"gmail": "Gmail", "slack": "Slack", "monday": "Monday.com", "nyt": "New York Times"}


def fake_fetch(url):
    if url not in PAGES:
        raise AssertionError(f"unexpected fetch: {url}")
    return PAGES[url]


class ParseCatalogTests(unittest.TestCase):
    def test_reads_groups_apps_and_popularity(self):
        groups, apps, popular = ref.parse_catalog(MODULE)
        self.assertEqual(
            groups[0], {"key": "communication", "label": "Communication", "categories": ["Email", "Messaging"]}
        )
        self.assertEqual([a["slug"] for a in apps], ["gmail", "slack", "monday-com", "code-by-lodol"])
        self.assertEqual(apps[0]["icon"], "/app-icons/gmail-icon.png")
        self.assertEqual(apps[0]["categories"], ["Email", "Google"])
        self.assertEqual(popular[:3], ["gmail", "slack", "monday-com"])

    def test_an_app_without_groups_is_still_read(self):
        _, apps, _ = ref.parse_catalog(MODULE)
        self.assertEqual(apps[1]["categories"], ["Messaging"])

    def test_a_changed_shape_stops_with_an_explanation(self):
        with self.assertRaises(SystemExit) as raised:
            ref.parse_catalog("var e=[];")
        self.assertIn("changed shape", str(raised.exception))


class CatalogModuleTests(unittest.TestCase):
    def test_follows_the_page_to_its_data_module(self):
        self.assertEqual(ref.catalog_module(fake_fetch), MODULE)

    def test_a_missing_script_stops_with_an_explanation(self):
        with self.assertRaises(SystemExit) as raised:
            ref.catalog_module(lambda url: "<html></html>")
        self.assertIn("the directory's script", str(raised.exception))


class MatchAppsTests(unittest.TestCase):
    def test_by_slug_then_by_name(self):
        _, apps, _ = ref.parse_catalog(MODULE)
        matched = ref.match_apps(apps, PROVIDERS)
        self.assertEqual(matched["gmail"]["slug"], "gmail")
        self.assertEqual(matched["monday"]["slug"], "monday-com")
        self.assertNotIn("nyt", matched)

    def test_lodol_s_own_steps_are_not_apps(self):
        _, apps, _ = ref.parse_catalog(MODULE)
        self.assertNotIn("code-by-lodol", {a["slug"] for a in ref.match_apps(apps, PROVIDERS).values()})


class RefreshTests(unittest.TestCase):
    def test_builds_the_groups_and_popularity(self):
        data = ref.refresh(fake_fetch, PROVIDERS)
        self.assertEqual(set(data), {"about", "groups", "popular"})
        self.assertEqual([g["key"] for g in data["groups"]], ["communication", "app_families"])
        # By provider id, and only apps the docs have: Lodol's own steps and
        # the filler slugs are left out.
        self.assertEqual(data["popular"], ["gmail", "slack", "monday"])

    def test_main_writes_the_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            actions = Path(tmp) / "actions"
            actions.mkdir()
            for pid, name in PROVIDERS.items():
                (actions / f"{pid}.json").write_text(json.dumps({"id": pid, "display_name": name}))
            (actions / "skipflow_text.json").write_text(json.dumps({"id": "skipflow_text"}))
            output = Path(tmp) / "directory.json"

            original = ref.fetch, ref.ACTIONS_DIR
            ref.fetch, ref.ACTIONS_DIR = fake_fetch, actions
            try:
                with contextlib.redirect_stdout(io.StringIO()) as out:
                    ref.main(["--output", str(output)])
            finally:
                ref.fetch, ref.ACTIONS_DIR = original

            data = json.loads(output.read_text())
            self.assertEqual(data["popular"], ["gmail", "slack", "monday"])
            self.assertIn("Popular apps : 3", out.getvalue())


if __name__ == "__main__":
    unittest.main()
