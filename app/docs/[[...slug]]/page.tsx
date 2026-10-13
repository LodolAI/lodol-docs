import { source } from '@/lib/source';
import {
  DocsBody,
  DocsDescription,
  DocsPage,
  DocsTitle,
} from 'fumadocs-ui/layouts/notebook/page';
import { notFound } from 'next/navigation';
import { getMDXComponents } from '@/mdx-components';
import { IntegrationIcon } from '@/components/integration-icon';
import type { Metadata } from 'next';

type PageData = NonNullable<ReturnType<typeof source.getPage>>['data'];

function counted(count: number, noun: string): string {
  return `${count} ${noun}${count === 1 ? '' : 's'}`;
}

/**
 * An app or built-in step page: its logo or icon beside the title, then
 * what it is: "App · Email · 14 actions · 1 trigger".
 */
function IntegrationHeader({ data }: { data: PageData }) {
  const builtIn = data.integration === 'built-in';
  const facts = [
    builtIn ? 'Built-in step' : 'App',
    data.category,
    counted(data.actions ?? 0, builtIn ? 'step' : 'action'),
    data.triggers ? counted(data.triggers, 'trigger') : undefined,
  ].filter(Boolean);
  return (
    <div className="flex items-start gap-4">
      <IntegrationIcon
        name={data.title}
        icon={typeof data.icon === 'string' ? data.icon : undefined}
        logo={data.logo}
        builtIn={builtIn}
        size="lg"
        className="mt-1"
      />
      <div className="min-w-0 flex-1">
        <DocsTitle className="lodol-page-title">{data.title}</DocsTitle>
        <p className="mt-1 text-sm text-fd-muted-foreground">{facts.join(' · ')}</p>
      </div>
    </div>
  );
}

export default async function Page(props: {
  params: Promise<{ slug?: string[] }>;
}) {
  const params = await props.params;
  const page = source.getPage(params.slug);
  if (!page) notFound();

  const { body: MDX, toc } = await page.data.load();

  return (
    <DocsPage toc={toc} full={page.data.full}>
      {page.data.integration ? (
        <IntegrationHeader data={page.data} />
      ) : (
        <DocsTitle className="lodol-page-title">{page.data.title}</DocsTitle>
      )}
      <DocsDescription>{page.data.description}</DocsDescription>
      <DocsBody>
        <MDX components={getMDXComponents()} />
      </DocsBody>
    </DocsPage>
  );
}

export async function generateStaticParams() {
  return source.generateParams();
}

export async function generateMetadata(props: {
  params: Promise<{ slug?: string[] }>;
}): Promise<Metadata> {
  const params = await props.params;
  const page = source.getPage(params.slug);
  if (!page) notFound();

  return {
    title: page.data.title,
    description: page.data.description,
    // The page in Markdown, for AI tools (see lib/llms.ts).
    alternates: { types: { 'text/markdown': `${page.url}.md` } },
  };
}
