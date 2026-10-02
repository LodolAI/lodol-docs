import { defineConfig, defineDocs } from 'fumadocs-mdx/config';

export const docs = defineDocs({
  dir: 'content/docs',
  // Load each page's compiled body when that page renders. Importing them all
  // up front (the default) ran the production build out of memory on CI once
  // the action reference grew to ~770 pages.
  docs: { async: true },
});

export default defineConfig();
