import type { MetadataRoute } from 'next';
import { SITE } from './sitemap';

/**
 * /robots.txt: every crawler, AI assistants' included, may read the docs, and
 * is pointed at the sitemap. The docs are also summarized for AI in
 * /llms.txt and /llms-full.txt (scripts/render-llms.py).
 */
export default function robots(): MetadataRoute.Robots {
  return {
    rules: [{ userAgent: '*', allow: '/', disallow: '/api/' }],
    sitemap: `${SITE}/sitemap.xml`,
  };
}
