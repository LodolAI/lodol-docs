import type { MetadataRoute } from 'next';
import { source } from '@/lib/source';

/** Where the docs are served, as in the root layout's metadataBase. */
export const SITE = 'https://docs.lodol.com';

/**
 * /sitemap.xml: the home page and every docs page Fumadocs knows, the ~850
 * integration pages included, so search engines and AI assistants find a new
 * page without waiting to follow a link to it. Built from the same source as
 * the sidebar, so a page added or removed is in or out of it with no list to
 * keep.
 */
export default function sitemap(): MetadataRoute.Sitemap {
  return [{ url: `${SITE}/` }, ...source.getPages().map((page) => ({ url: `${SITE}${page.url}` }))];
}
