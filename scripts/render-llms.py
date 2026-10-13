#!/usr/bin/env python3
"""Write the docs' files for AI tools into ``public/``.

* a Markdown copy of each hand-written page, at its address plus ``.md``:
  ``/docs/concepts/runs.md``, and ``/docs.md`` for the first page;
* ``/llms.txt``, which says what Lodol is and lists every page, linking to
  its Markdown copy;
* ``/llms-full.txt``, with every hand-written page in one file.

The integration pages' copies, and the directory's, are written with those
pages by ``render-actions-docs.py``, which runs first. All of them are
static files, which the site serves as they are: served as routes, they
would compile the site's page source a second time and slow every build.

Usage::

    python scripts/render-llms.py
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
from dataclasses import dataclass
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
DOCS_ROOT = SCRIPT_DIR.parent
DEFAULT_CONTENT_DIR = DOCS_ROOT / "content" / "docs"
DEFAULT_PUBLIC_DIR = DOCS_ROOT / "public"

#: The docs' address, for links in files that are read away from the site.
SITE_URL = "https://docs.lodol.com"

#: The folder render-actions-docs.py generates, with its own Markdown copies.
GENERATED = "integrations"

SUMMARY = (
    "Lodol is a workflow automation platform. A workflow starts when something "
    "happens in one of your apps, on a schedule or on demand, and runs the same "
    "steps every time. These docs explain how workflows work, how to build them "
    "yourself or with an AI tool, every app and built-in step a workflow can use, "
    "and the developer API."
)


@dataclass
class Page:
    url: str
    title: str
    description: str
    #: The page's source, without its front matter.
    body: str


def markdown_url(path: str) -> str:
    """A page's Markdown copy: ``/docs/runs`` is ``https://docs.lodol.com/docs/runs.md``."""
    return f"{SITE_URL}{path}.md"


# ---------------------------------------------------------------------------
# Reading pages, in the sidebar's order
# ---------------------------------------------------------------------------

def _unquote(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] == '"':
        try:
            return json.loads(value)
        except ValueError:
            return value[1:-1]
    if len(value) >= 2 and value[0] == value[-1] == "'":
        return value[1:-1].replace("''", "'")
    return value


def split_front_matter(text: str) -> tuple[dict[str, str], str]:
    """A page's front matter, as ``key: value`` lines, and the rest."""
    match = re.match(r"---\r?\n(.*?)\r?\n---\r?\n", text, re.S)
    if not match:
        return {}, text
    meta = {}
    for line in match.group(1).splitlines():
        key, sep, value = line.partition(":")
        if sep and key.strip() and not line[:1].isspace():
            meta[key.strip()] = _unquote(value.strip())
    return meta, text[match.end():]


def read_page(path: Path, url: str) -> Page:
    meta, body = split_front_matter(path.read_text(encoding="utf-8"))
    return Page(url, meta.get("title", ""), meta.get("description", ""), body)


def _meta(folder: Path) -> dict:
    path = folder / "meta.json"
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


def _is_group(name: str) -> bool:
    """A folder group, ``(docs)``: its name isn't part of any address."""
    return name.startswith("(") and name.endswith(")")


def pages_in(folder: Path, url: str) -> list[Page]:
    """A folder's pages in its ``meta.json`` order, as the sidebar lists
    them. ``url`` is the folder's address."""
    entries = sorted(
        [p.stem for p in folder.glob("*.mdx")] + [p.name for p in folder.iterdir() if p.is_dir()],
        key=lambda name: (name != "index", name),
    )
    listed = _meta(folder).get("pages") or ["..."]
    # "...name" spreads a folder's pages in place; "..." alone adds the rest.
    explicit = {n[3:] if n.startswith("...") else n for n in listed}
    names: list[str] = []
    for name in listed:
        if name.startswith("---"):
            continue
        if name == "...":
            names += [n for n in entries if n not in explicit and n not in names]
        else:
            names.append(name[3:] if name.startswith("...") else name)

    pages: list[Page] = []
    for name in names:
        if (folder / name).is_dir():
            pages += pages_in(folder / name, url if _is_group(name) else f"{url}/{name}")
        elif (folder / f"{name}.mdx").exists():
            pages.append(read_page(folder / f"{name}.mdx", url if name == "index" else f"{url}/{name}"))
    return pages


def doc_sections(content_dir: Path) -> list[tuple[str, list[Page]]]:
    """The hand-written pages by tab (Documentation, API), each tab's pages
    in order. The generated integrations tab is left out."""
    sections = []
    for name in _meta(content_dir).get("pages") or []:
        folder = content_dir / name
        if name == GENERATED or not folder.is_dir():
            continue
        pages = pages_in(folder, "/docs" if _is_group(name) else f"/docs/{name}")
        if pages:
            sections.append((_meta(folder).get("title") or name, pages))
    return sections


# ---------------------------------------------------------------------------
# Writing them
# ---------------------------------------------------------------------------

def apps_with_triggers(catalog: dict) -> str:
    """The apps a workflow can start from, for the triggers page's list."""
    return "\n".join(
        f"- [{e['name']}]({markdown_url(e['href'])})"
        for e in catalog.get("entries", [])
        if not e.get("builtIn") and e.get("triggers")
    )


_DOCS_LINK_RE = re.compile(r"\]\((/docs(?:/[^)\s#]*)?)(#[^)\s]*)?\)")


def page_markdown(page: Page, catalog: dict) -> str:
    """A page in Markdown: its title, summary and address, then its source.
    Links to other pages point at their Markdown copies, and the list of
    apps with triggers is written out."""
    body = page.body.replace("<AppsWithTriggers />", apps_with_triggers(catalog))
    body = _DOCS_LINK_RE.sub(lambda m: f"]({markdown_url(m.group(1))}{m.group(2) or ''})", body)
    head = [f"# {page.title}", ""]
    if page.description:
        head += [f"> {page.description}", ""]
    head += [f"Web page: {SITE_URL}{page.url}", ""]
    return "\n".join(head + [body.strip(), ""])


def llms_index(sections: list[tuple[str, list[Page]]], catalog: dict) -> str:
    """``/llms.txt``: what Lodol is, and every page."""
    lines = [
        "# Lodol Docs",
        "",
        f"> {SUMMARY}",
        "",
        "Every page is also available as Markdown: add `.md` to its address. For "
        "Lodol's product, pricing and company, see https://www.lodol.com/llms.txt.",
        "",
    ]
    for title, pages in sections:
        lines += [f"## {title}", ""]
        for page in pages:
            description = f": {page.description}" if page.description else ""
            lines.append(f"- [{page.title}]({markdown_url(page.url)}){description}")
        lines.append("")
    lines += [
        "## Integrations",
        "",
        f"- [Integrations]({markdown_url('/docs/integrations')}): The {catalog.get('apps', 0)} "
        "apps and the built-in steps a workflow can use, one line each, linking to a "
        "page with each one's triggers and actions and their inputs and outputs.",
        "",
        "## Optional",
        "",
        f"- [Full documentation]({SITE_URL}/llms-full.txt): Every page under "
        f"{' and '.join(title for title, _ in sections)} above, in one file.",
        "",
    ]
    return "\n".join(lines)


def _clear(public_dir: Path) -> None:
    """Remove what an earlier run wrote, so a deleted page leaves no copy.
    The integration copies belong to render-actions-docs.py."""
    for name in ("llms.txt", "llms-full.txt", "docs.md"):
        (public_dir / name).unlink(missing_ok=True)
    docs = public_dir / "docs"
    if docs.is_dir():
        for child in docs.iterdir():
            if child.name in (GENERATED, f"{GENERATED}.md"):
                continue
            if child.is_dir():
                shutil.rmtree(child)
            else:
                child.unlink()


def render(content_dir: Path, public_dir: Path) -> int:
    """Write every file. Returns how many pages were copied."""
    catalog_path = content_dir / GENERATED / "catalog.json"
    catalog = json.loads(catalog_path.read_text(encoding="utf-8")) if catalog_path.exists() else {}
    sections = doc_sections(content_dir)
    pages = [page for _, pages in sections for page in pages]

    _clear(public_dir)
    texts = []
    for page in pages:
        text = page_markdown(page, catalog)
        path = public_dir / f"{page.url.lstrip('/')}.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        texts.append(text)
    (public_dir / "llms.txt").write_text(llms_index(sections, catalog), encoding="utf-8")
    (public_dir / "llms-full.txt").write_text("\n".join(texts), encoding="utf-8")
    return len(pages)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--content-dir", type=Path, default=DEFAULT_CONTENT_DIR)
    parser.add_argument("--public-dir", type=Path, default=DEFAULT_PUBLIC_DIR)
    args = parser.parse_args(argv)
    count = render(args.content_dir, args.public_dir)
    print(f"Wrote llms.txt, llms-full.txt and {count} Markdown copies to {args.public_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
