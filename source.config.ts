import { defineConfig, defineDocs } from 'fumadocs-mdx/config';
import { rehypeCodeOutsideActionReference } from './lib/rehype-code';

export const docs = defineDocs({
  dir: 'content/docs',
  // Load each page's compiled body when that page renders. Importing them all
  // up front (the default) ran the production build out of memory on CI once
  // the action reference grew to ~770 pages.
  docs: { async: true },
});

export default defineConfig({
  mdxOptions: {
    // Highlight code as pages compile everywhere but the action reference,
    // whose ~9,000 examples ran the build out of memory. See lib/rehype-code.ts.
    rehypeCodeOptions: false,
    rehypePlugins: [rehypeCodeOutsideActionReference],
  },
});
