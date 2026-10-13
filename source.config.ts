import { defineConfig, defineDocs, frontmatterSchema } from 'fumadocs-mdx/config';
import { z } from 'zod';
import { rehypeCodeOutsideIntegrationReference } from './lib/rehype-code';

export const docs = defineDocs({
  dir: 'content/docs',
  docs: {
    // Load each page's compiled body when that page renders. Importing them all
    // up front (the default) ran the production build out of memory on CI once
    // the integration reference grew to ~770 pages.
    async: true,
    schema: frontmatterSchema.extend({
      // Set on the pages scripts/render-actions-docs.py generates, so the page
      // header can show the integration's tile and how many actions it has.
      integration: z.enum(['app', 'built-in']).optional(),
      actions: z.number().int().nonnegative().optional(),
    }),
  },
});

export default defineConfig({
  mdxOptions: {
    // Highlight code as pages compile everywhere but the integration
    // reference, whose ~9,000 examples ran the build out of memory. See
    // lib/rehype-code.ts.
    rehypeCodeOptions: false,
    rehypePlugins: [rehypeCodeOutsideIntegrationReference],
  },
});
