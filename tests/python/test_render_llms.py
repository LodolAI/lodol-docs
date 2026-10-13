"""Unit tests for ``scripts/render-llms.py``, which writes the docs' files
for AI tools: a Markdown copy of each hand-written page, ``/llms.txt`` and
``/llms-full.txt``. The tests build a small content tree in a temporary
folder.
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


SCRIPT_PATH = Path(__file__).resolve().parents[2] / "scripts" / "render-llms.py"


def _load_script():
    spec = importlib.util.spec_from_file_location("render_llms", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    sys.modules["render_llms"] = module
    spec.loader.exec_module(module)
    return module


llms = _load_script()

CATALOG = {
    "apps": 833,
    "entries": [
        {"name": "Gmail", "href": "/docs/integrations/gmail", "builtIn": False, "triggers": 1},
        {"name": "Notion", "href": "/docs/integrations/notion", "builtIn": False},
        {"name": "Schedule", "href": "/docs/integrations/built-in/schedule", "builtIn": True, "triggers": 1},
    ],
}

FILES = {
    "meta.json": {"pages": ["(docs)", "integrations", "api"]},
    "(docs)/meta.json": {"title": "Documentation", "pages": ["---Get started---", "index", "...concepts"]},
    "(docs)/index.mdx": (
        '---\ntitle: "What is \\"Lodol\\"?"\ndescription: Lodol runs your automations.\nicon: House\n---\n\n'
        "See [runs](/docs/concepts/runs#statuses), [Gmail](/docs/integrations/gmail) "
        "and [Lodol](https://www.lodol.com).\n"
    ),
    "(docs)/concepts/meta.json": {"title": "Concepts", "pages": ["triggers", "runs"]},
    "(docs)/concepts/triggers.mdx": "---\ntitle: Triggers\ndescription: What starts a run.\n---\n\nThese apps have triggers:\n\n<AppsWithTriggers />\n",
    "(docs)/concepts/runs.mdx": "---\ntitle: Runs\n---\n\nA run is one pass.\n",
    "api/meta.json": {"title": "API", "pages": ["index", "..."]},
    "api/index.mdx": "---\ntitle: Developer API\ndescription: 'Run workflows from code.'\n---\n\nBase URL.\n",
    "api/runs.mdx": "---\ntitle: Runs\ndescription: Start a run.\n---\n\nPOST.\n",
    "api/auth.mdx": "---\ntitle: Authentication\ndescription: Keys.\n---\n\nBearer.\n",
    "integrations/catalog.json": CATALOG,
    "integrations/gmail.mdx": "---\ntitle: Gmail\n---\n\nGenerated.\n",
}


def _content(root: Path) -> Path:
    content = root / "content" / "docs"
    for name, value in FILES.items():
        path = content / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value) if isinstance(value, dict) else value, encoding="utf-8")
    return content


class FrontMatterTests(unittest.TestCase):
    def test_reads_plain_and_quoted_values(self):
        meta, body = llms.split_front_matter(
            '---\ntitle: "A \\"quoted\\" title"\ndescription: \'It\'\'s fine: really\'\nicon: Zap\n---\nBody\n'
        )
        self.assertEqual(meta["title"], 'A "quoted" title')
        self.assertEqual(meta["description"], "It's fine: really")
        self.assertEqual(body, "Body\n")

    def test_keeps_colons_after_the_first(self):
        meta, _ = llms.split_front_matter("---\ndescription: One: two\n---\n")
        self.assertEqual(meta["description"], "One: two")

    def test_a_page_without_front_matter(self):
        self.assertEqual(llms.split_front_matter("Just text."), ({}, "Just text."))


class OrderTests(unittest.TestCase):
    def test_sections_follow_the_sidebar_and_skip_the_generated_tab(self):
        with tempfile.TemporaryDirectory() as tmp:
            sections = llms.doc_sections(_content(Path(tmp)))
        self.assertEqual([title for title, _ in sections], ["Documentation", "API"])
        self.assertEqual(
            [page.url for page in sections[0][1]],
            ["/docs", "/docs/concepts/triggers", "/docs/concepts/runs"],
        )

    def test_the_rest_marker_adds_unlisted_pages_by_name(self):
        with tempfile.TemporaryDirectory() as tmp:
            sections = llms.doc_sections(_content(Path(tmp)))
        self.assertEqual(
            [page.url for page in sections[1][1]], ["/docs/api", "/docs/api/auth", "/docs/api/runs"]
        )


class PageMarkdownTests(unittest.TestCase):
    def _page(self, url):
        with tempfile.TemporaryDirectory() as tmp:
            pages = [p for _, ps in llms.doc_sections(_content(Path(tmp))) for p in ps]
        return next(p for p in pages if p.url == url)

    def test_starts_with_the_title_summary_and_address(self):
        text = llms.page_markdown(self._page("/docs"), CATALOG)
        self.assertTrue(
            text.startswith(
                '# What is "Lodol"?\n\n> Lodol runs your automations.\n\n'
                "Web page: https://docs.lodol.com/docs\n\nSee "
            )
        )
        self.assertNotIn("icon: House", text)

    def test_points_docs_links_at_markdown_copies(self):
        text = llms.page_markdown(self._page("/docs"), CATALOG)
        self.assertIn("[runs](https://docs.lodol.com/docs/concepts/runs.md#statuses)", text)
        self.assertIn("[Gmail](https://docs.lodol.com/docs/integrations/gmail.md)", text)
        self.assertIn("[Lodol](https://www.lodol.com)", text)

    def test_writes_out_the_apps_with_triggers(self):
        text = llms.page_markdown(self._page("/docs/concepts/triggers"), CATALOG)
        self.assertIn("- [Gmail](https://docs.lodol.com/docs/integrations/gmail.md)", text)
        self.assertNotIn("Notion", text)
        self.assertNotIn("Schedule", text)
        self.assertNotIn("<AppsWithTriggers", text)

    def test_a_page_without_a_description(self):
        text = llms.page_markdown(self._page("/docs/concepts/runs"), CATALOG)
        self.assertTrue(text.startswith("# Runs\n\nWeb page: "))


class RenderTests(unittest.TestCase):
    def test_writes_every_file_where_its_address_says(self):
        with tempfile.TemporaryDirectory() as tmp:
            content, public = _content(Path(tmp)), Path(tmp) / "public"
            self.assertEqual(llms.render(content, public), 6)
            for path in ("docs.md", "docs/concepts/runs.md", "docs/api.md", "docs/api/runs.md"):
                self.assertTrue((public / path).exists(), path)
            index = (public / "llms.txt").read_text()
            full = (public / "llms-full.txt").read_text()
        self.assertTrue(index.startswith("# Lodol Docs\n\n> Lodol is a workflow automation platform."))
        self.assertIn(
            "## Documentation\n\n- [What is \"Lodol\"?](https://docs.lodol.com/docs.md): "
            "Lodol runs your automations.\n",
            index,
        )
        self.assertIn("- [Authentication](https://docs.lodol.com/docs/api/auth.md): Keys.\n", index)
        self.assertIn("- [Integrations](https://docs.lodol.com/docs/integrations.md): The 833 apps", index)
        self.assertIn("Every page under Documentation and API above", index)
        self.assertNotIn("Generated.", full)
        self.assertEqual(full.count("\nWeb page: "), 6)

    def test_clears_its_own_old_files_and_leaves_the_integration_copies(self):
        with tempfile.TemporaryDirectory() as tmp:
            content, public = _content(Path(tmp)), Path(tmp) / "public"
            (public / "docs" / "integrations").mkdir(parents=True)
            (public / "docs" / "integrations" / "gmail.md").write_text("Gmail")
            (public / "docs" / "integrations.md").write_text("Directory")
            (public / "docs" / "removed.md").write_text("Old page")
            (public / "docs" / "old-folder").mkdir()
            llms.render(content, public)
            self.assertFalse((public / "docs" / "removed.md").exists())
            self.assertFalse((public / "docs" / "old-folder").exists())
            self.assertTrue((public / "docs" / "integrations" / "gmail.md").exists())
            self.assertTrue((public / "docs" / "integrations.md").exists())

    def test_main(self):
        with tempfile.TemporaryDirectory() as tmp:
            content, public = _content(Path(tmp)), Path(tmp) / "public"
            with contextlib.redirect_stdout(io.StringIO()) as out:
                self.assertEqual(llms.main(["--content-dir", str(content), "--public-dir", str(public)]), 0)
            self.assertIn("6 Markdown copies", out.getvalue())


if __name__ == "__main__":
    unittest.main()
