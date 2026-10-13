import { llmsFull, llmsIndex, markdownUrl, pageMarkdown } from '@/lib/llms';
import { source } from '@/lib/source';

type FakePage = {
  url: string;
  slugs: string[];
  data: { title: string; description?: string; getText: () => Promise<string> };
};

function page(url: string, title: string, raw: string, description?: string): FakePage {
  const slugs = url.split('/').filter(Boolean).slice(1);
  return { url, slugs, data: { title, description, getText: async () => raw } };
}

const pages: Record<string, FakePage> = {
  '/docs': page('/docs', 'What is Lodol?', '---\ntitle: What is Lodol?\n---\n\nRead [runs](/docs/concepts/runs#statuses) and [Gmail](/docs/integrations/gmail).\n', 'Lodol runs your automations.'),
  '/docs/concepts/triggers': page('/docs/concepts/triggers', 'Triggers', '---\ntitle: Triggers\n---\n\nThese apps have triggers:\n\n<AppsWithTriggers />\n', 'What starts a run.'),
  '/docs/api': page('/docs/api', 'Developer API', 'Base URL.', 'Run workflows from code.'),
  '/docs/integrations/gmail': page('/docs/integrations/gmail', 'Gmail', 'Generated.'),
};

const tree = {
  name: 'Docs',
  children: [
    {
      type: 'folder',
      name: 'Documentation',
      children: [
        { type: 'separator', name: 'Get started' },
        { type: 'page', url: '/docs' },
        { type: 'page', url: '/docs/concepts/triggers' },
      ],
    },
    {
      type: 'folder',
      name: 'Integrations',
      index: { type: 'page', url: '/docs/integrations' },
      children: [{ type: 'page', url: '/docs/integrations/gmail' }],
    },
    { type: 'folder', name: 'API', children: [{ type: 'page', url: '/docs/api' }] },
  ],
};

jest.mock('@/lib/source', () => ({
  source: {
    get pageTree() {
      return tree;
    },
    getNodePage: (node: { url: string }) => pages[node.url],
    getPage: (slugs: string[] = []) => pages[['/docs', ...slugs].join('/')],
  },
}));

jest.mock('@/lib/catalog', () => ({
  getCatalog: () => ({
    apps: 833,
    entries: [
      { id: 'gmail', name: 'Gmail', href: '/docs/integrations/gmail', builtIn: false, triggers: 1 },
      { id: 'notion', name: 'Notion', href: '/docs/integrations/notion', builtIn: false },
      { id: 'skipflow_schedule', name: 'Schedule', href: '/docs/integrations/built-in/schedule', builtIn: true },
    ],
  }),
}));

describe('markdownUrl', () => {
  it('adds .md to the page address on the docs site', () => {
    expect(markdownUrl('/docs')).toBe('https://docs.lodol.com/docs.md');
    expect(markdownUrl('/docs/api/runs')).toBe('https://docs.lodol.com/docs/api/runs.md');
  });
});

describe('pageMarkdown', () => {
  it('starts with the title, summary and web page, without the front matter', async () => {
    const text = await pageMarkdown(source.getPage([])!);
    expect(text.startsWith('# What is Lodol?\n\n> Lodol runs your automations.\n\nWeb page: https://docs.lodol.com/docs\n\n')).toBe(true);
    expect(text).not.toContain('title: What is Lodol?');
  });

  it('points links at the Markdown copies, keeping anchors', async () => {
    const text = await pageMarkdown(source.getPage([])!);
    expect(text).toContain('[runs](https://docs.lodol.com/docs/concepts/runs.md#statuses)');
    expect(text).toContain('[Gmail](https://docs.lodol.com/docs/integrations/gmail.md)');
  });

  it('writes out the apps with triggers', async () => {
    const text = await pageMarkdown(source.getPage(['concepts', 'triggers'])!);
    expect(text).toContain('- [Gmail](https://docs.lodol.com/docs/integrations/gmail.md)');
    expect(text).not.toContain('Notion');
    expect(text).not.toContain('<AppsWithTriggers');
  });
});

describe('llmsIndex', () => {
  const index = llmsIndex();

  it('says what Lodol is and where the Markdown copies are', () => {
    expect(index.startsWith('# Lodol Docs\n\n> Lodol is a workflow automation platform.')).toBe(true);
    expect(index).toContain('add `.md` to its address');
    expect(index).toContain('https://www.lodol.com/llms.txt');
  });

  it('lists the hand-written pages by tab, in sidebar order', () => {
    expect(index).toContain(
      '## Documentation\n\n' +
        '- [What is Lodol?](https://docs.lodol.com/docs.md): Lodol runs your automations.\n' +
        '- [Triggers](https://docs.lodol.com/docs/concepts/triggers.md): What starts a run.\n',
    );
    expect(index).toContain('## API\n\n- [Developer API](https://docs.lodol.com/docs/api.md): Run workflows from code.\n');
    expect(index.indexOf('## Documentation')).toBeLessThan(index.indexOf('## API'));
  });

  it('points at the integrations directory instead of listing every app', () => {
    expect(index).toContain('- [Integrations](https://docs.lodol.com/docs/integrations.md): The 833 apps');
    expect(index).not.toContain('/docs/integrations/gmail.md');
    expect(index).toContain('[Full documentation](https://docs.lodol.com/llms-full.txt)');
  });
});

describe('llmsFull', () => {
  it('holds every hand-written page in order, and no generated ones', async () => {
    const text = await llmsFull();
    const titles = [...text.matchAll(/^# (.+)$/gm)].map((match) => match[1]);
    expect(titles).toEqual(['What is Lodol?', 'Triggers', 'Developer API']);
  });
});
