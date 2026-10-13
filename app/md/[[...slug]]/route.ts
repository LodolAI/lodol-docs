import { notFound } from 'next/navigation';
import { source } from '@/lib/source';
import { handWrittenPages, isGenerated, pageMarkdown } from '@/lib/llms';

// A hand-written page's Markdown copy. next.config.mjs sends /docs/<page>.md
// here; the integration pages' copies are files in public/ and come first.

export const dynamic = 'force-static';
export const dynamicParams = false;

export async function GET(
  _request: Request,
  { params }: { params: Promise<{ slug?: string[] }> },
) {
  const { slug } = await params;
  const page = source.getPage(slug);
  if (!page || isGenerated(page)) notFound();
  return new Response(await pageMarkdown(page), {
    headers: { 'Content-Type': 'text/markdown; charset=utf-8' },
  });
}

export function generateStaticParams() {
  return handWrittenPages().map((page) => ({ slug: page.slugs }));
}
