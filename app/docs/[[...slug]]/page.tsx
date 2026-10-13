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

/** An app or built-in step page: its tile beside the title, and a count. */
function IntegrationHeader({ data }: { data: PageData }) {
  const builtIn = data.integration === 'built-in';
  const count = data.actions ?? 0;
  const noun = builtIn ? 'step' : 'action';
  return (
    <div className="flex items-start gap-4">
      <IntegrationIcon
        name={data.title}
        icon={typeof data.icon === 'string' ? data.icon : undefined}
        builtIn={builtIn}
        size="lg"
        className="mt-1"
      />
      <div className="min-w-0 flex-1">
        <DocsTitle className="lodol-page-title">{data.title}</DocsTitle>
        <p className="mt-1 text-sm text-fd-muted-foreground">
          {builtIn ? 'Built-in step' : 'App'} · {count} {noun}
          {count === 1 ? '' : 's'}
        </p>
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
  };
}
