import type { Folder, Node } from 'fumadocs-core/page-tree';
import { source } from '@/lib/source';
import { getCatalog } from '@/lib/catalog';

// The docs for AI tools: /llms.txt lists every page, /llms-full.txt holds
// the hand-written ones in full, and each page has a Markdown copy at its
// address plus `.md`. The integration pages' copies are written with the
// pages themselves, by scripts/render-actions-docs.py, into public/.

/** The docs' address, for links that are read away from the site. */
export const SITE_URL = 'https://docs.lodol.com';

type Page = NonNullable<ReturnType<typeof source.getPage>>;

/** A page generated from data/actions, whose Markdown copy is in public/. */
export function isGenerated(page: Page): boolean {
  return page.slugs[0] === 'integrations';
}

/** A page's Markdown copy: `/docs/runs` is `https://docs.lodol.com/docs/runs.md`. */
export function markdownUrl(path: string): string {
  return `${SITE_URL}${path}.md`;
}

function pagesIn(folder: Folder): Page[] {
  const pages: Page[] = [];
  const visit = (node: Node) => {
    if (node.type === 'page') {
      const page = source.getNodePage(node);
      if (page) pages.push(page);
    } else if (node.type === 'folder') {
      if (node.index) visit(node.index);
      node.children.forEach(visit);
    }
  };
  visit(folder);
  return pages;
}

/** The hand-written pages, by tab (Documentation, API) in the sidebar's order. */
export function docSections(): { title: string; pages: Page[] }[] {
  return source.pageTree.children.flatMap((node) => {
    if (node.type !== 'folder') return [];
    const pages = pagesIn(node).filter((page) => !isGenerated(page));
    return pages.length > 0 ? [{ title: String(node.name), pages }] : [];
  });
}

export function handWrittenPages(): Page[] {
  return docSections().flatMap((section) => section.pages);
}

/** The apps a workflow can start from, for the triggers page's list. */
function appsWithTriggers(): string {
  return getCatalog()
    .entries.filter((entry) => !entry.builtIn && entry.triggers)
    .map((entry) => `- [${entry.name}](${markdownUrl(entry.href)})`)
    .join('\n');
}

/**
 * A hand-written page in Markdown: its title and summary, then its source
 * without the front matter. Links to other pages point at their Markdown
 * copies, and the list of apps with triggers is written out.
 */
export async function pageMarkdown(page: Page): Promise<string> {
  const raw = await page.data.getText('raw');
  const body = raw
    .replace(/^---\r?\n[\s\S]*?\r?\n---\r?\n/, '')
    .replace(/<AppsWithTriggers\s*\/>/g, appsWithTriggers)
    .replace(/\]\((\/docs(?:\/[^)\s#]*)?)(#[^)\s]*)?\)/g, (_, path: string, hash = '') => `](${markdownUrl(path)}${hash})`)
    .trim();
  const head = [`# ${page.data.title}`, ''];
  if (page.data.description) head.push(`> ${page.data.description}`, '');
  head.push(`Web page: ${SITE_URL}${page.url}`, '');
  return `${[...head, body].join('\n')}\n`;
}

/** /llms.txt: what Lodol is, and every page, linking to its Markdown copy. */
export function llmsIndex(): string {
  const { apps } = getCatalog();
  const lines = [
    '# Lodol Docs',
    '',
    '> Lodol is a workflow automation platform. A workflow starts when something happens in one of your apps, on a schedule or on demand, and runs the same steps every time. These docs explain how workflows work, how to build them yourself or with an AI tool, every app and built-in step a workflow can use, and the developer API.',
    '',
    "Every page is also available as Markdown: add `.md` to its address. For Lodol's product, pricing and company, see https://www.lodol.com/llms.txt.",
    '',
  ];
  for (const section of docSections()) {
    lines.push(`## ${section.title}`, '');
    for (const page of section.pages) {
      const description = page.data.description ? `: ${page.data.description}` : '';
      lines.push(`- [${page.data.title}](${markdownUrl(page.url)})${description}`);
    }
    lines.push('');
  }
  lines.push(
    '## Integrations',
    '',
    `- [Integrations](${markdownUrl('/docs/integrations')}): The ${apps} apps and the built-in steps a workflow can use, one line each, linking to a page with each one's triggers and actions and their inputs and outputs.`,
    '',
    '## Optional',
    '',
    `- [Full documentation](${SITE_URL}/llms-full.txt): Every page under Documentation and API above, in one file.`,
    '',
  );
  return lines.join('\n');
}

/** /llms-full.txt: every hand-written page in Markdown, in order. */
export async function llmsFull(): Promise<string> {
  const pages = await Promise.all(handWrittenPages().map(pageMarkdown));
  return pages.join('\n');
}
