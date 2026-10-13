"""Unit tests for ``scripts/refresh-app-data.py``.

The script reads lodol.com's integrations directory and app pages, and
merges in trigger details from Lodol's MCP server. These tests feed it
small copies of those pages through a stub fetch, so they never touch the
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


SCRIPT_PATH = Path(__file__).resolve().parents[2] / "scripts" / "refresh-app-data.py"


def _load_script():
    spec = importlib.util.spec_from_file_location("refresh_app_data", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    sys.modules["refresh_app_data"] = module
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


def _app_page(triggers):
    items = "".join(
        f'<div class="_capItem_1"><span class="_capName_1asy0_233">{name}</span>'
        f'<span class="_capDesc_1asy0_240">{desc}</span></div>'
        for name, desc in triggers
    )
    count = (
        f'<span class="_stat_1"><strong>{len(triggers)}</strong> '
        f'trigger{"" if len(triggers) == 1 else "s"}</span>'
        if triggers else ""
    )
    section = (
        f'<h2 class="_capTitle_1">Triggers</h2><p>Kick off a workflow.</p>{items}'
        if triggers else ""
    )
    return (
        f'<div class="_stats_1"><span class="_stat_1"><strong>14</strong> actions</span>{count}</div>'
        f'<section class="_body_1">{section}<h2 class="_capTitle_1">Actions</h2></section>'
    )


PAGES = {
    f"{SITE}/integrations": DIRECTORY,
    f"{SITE}/_astro/Integrations.Ab12.js": COMPONENT,
    f"{SITE}/_astro/integrations.Cd-34.js": MODULE,
    f"{SITE}/integrations/gmail": _app_page([("Gmail New Email", "Triggers when a new email arrives &amp; more")]),
    f"{SITE}/integrations/slack": _app_page(
        [("New Slack message", "Runs when a message is posted."), ("Channel created", "Runs when a channel is made.")]
    ),
    f"{SITE}/integrations/monday-com": _app_page([]),
}

PROVIDERS = {"gmail": "Gmail", "slack": "Slack", "monday": "Monday.com", "nyt": "New York Times"}

GMAIL_DETAIL = {
    "id": "gmail_new_email_trigger",
    "display_name": "Gmail New Email",
    "description": "Triggers when a new email arrives in your Gmail inbox",
    "params": [{"name": "sender", "arg_index": 0, "required": False}],
    "output": {"email_id": "string"},
}


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


class ParseTriggersTests(unittest.TestCase):
    def test_reads_names_and_descriptions_in_order(self):
        triggers = ref.parse_triggers(PAGES[f"{SITE}/integrations/slack"])
        self.assertEqual(
            [t["display_name"] for t in triggers], ["New Slack message", "Channel created"]
        )

    def test_decodes_entities(self):
        (trigger,) = ref.parse_triggers(PAGES[f"{SITE}/integrations/gmail"])
        self.assertEqual(trigger["description"], "Triggers when a new email arrives & more")

    def test_an_app_without_triggers(self):
        self.assertEqual(ref.parse_triggers(PAGES[f"{SITE}/integrations/monday-com"]), [])

    def test_a_count_that_doesnt_match_stops(self):
        page = PAGES[f"{SITE}/integrations/slack"].replace("<strong>2</strong>", "<strong>3</strong>")
        with self.assertRaises(SystemExit):
            ref.parse_triggers(page)


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


class TriggerDetailsTests(unittest.TestCase):
    def test_owner_is_the_longest_matching_provider(self):
        providers = {"rackspace_email", "rackspace_email_admin"}
        self.assertEqual(
            ref._owner("rackspace_email_admin_new_mailbox_trigger", providers), "rackspace_email_admin"
        )
        self.assertEqual(ref._owner("rackspace_email_new_email_trigger", providers), "rackspace_email")
        self.assertIsNone(ref._owner("gmail_new_email_trigger", providers))

    def test_index_by_provider_from_each_shape(self):
        by_provider = ref.index_details({"gmail": [GMAIL_DETAIL]}, {"gmail"})
        from_list = ref.index_details([GMAIL_DETAIL], {"gmail"})
        from_apps = ref.index_details({"gmail": {"logo": "x", "triggers": [GMAIL_DETAIL]}}, {"gmail"})
        expected = {"gmail": {"Gmail New Email": GMAIL_DETAIL}}
        self.assertEqual(by_provider, expected)
        self.assertEqual(from_list, expected)
        self.assertEqual(from_apps, expected)

    def test_merge_keeps_the_site_s_order_and_adds_details(self):
        listed = [
            {"display_name": "New card", "description": "A card."},
            {"display_name": "Gmail New Email", "description": "Short."},
        ]
        merged = ref.merge_triggers(listed, {"Gmail New Email": GMAIL_DETAIL})
        self.assertEqual(merged, [listed[0], GMAIL_DETAIL])

    def test_details_without_filters_or_fields_dont_replace_the_site(self):
        bare = {"display_name": "New card", "description": "Old."}
        listed = [{"display_name": "New card", "description": "New."}]
        self.assertEqual(ref.merge_triggers(listed, {"New card": bare}), listed)


class RefreshTests(unittest.TestCase):
    def test_builds_the_app_data(self):
        known = {"gmail": {"Gmail New Email": GMAIL_DETAIL}}
        data = ref.refresh(fake_fetch, PROVIDERS, known, workers=1)
        self.assertEqual(data["popular"], ["gmail", "slack", "monday"])
        self.assertEqual(set(data["apps"]), {"gmail", "slack", "monday"})
        gmail = data["apps"]["gmail"]
        self.assertEqual(gmail["logo"], f"{SITE}/app-icons/gmail-icon.png")
        self.assertEqual(gmail["categories"], ["Email", "Google"])
        self.assertEqual(gmail["triggers"], [GMAIL_DETAIL])
        self.assertEqual(len(data["apps"]["slack"]["triggers"]), 2)
        self.assertNotIn("triggers", data["apps"]["monday"])

    def test_main_keeps_details_already_in_the_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            actions = Path(tmp) / "actions"
            actions.mkdir()
            for pid, name in PROVIDERS.items():
                (actions / f"{pid}.json").write_text(json.dumps({"id": pid, "display_name": name}))
            (actions / "skipflow_text.json").write_text(json.dumps({"id": "skipflow_text"}))
            output = Path(tmp) / "apps.json"
            output.write_text(json.dumps({"apps": {"gmail": {"triggers": [GMAIL_DETAIL]}}}))

            original = ref.fetch, ref.ACTIONS_DIR
            ref.fetch, ref.ACTIONS_DIR = fake_fetch, actions
            try:
                with contextlib.redirect_stdout(io.StringIO()) as out:
                    ref.main(["--output", str(output)])
            finally:
                ref.fetch, ref.ACTIONS_DIR = original

            data = json.loads(output.read_text())
            self.assertEqual(data["apps"]["gmail"]["triggers"], [GMAIL_DETAIL])
            self.assertIn("Not on lodol.com, so no logo or category: nyt", out.getvalue())
            self.assertIn("No filters or fields yet", out.getvalue())


if __name__ == "__main__":
    unittest.main()
