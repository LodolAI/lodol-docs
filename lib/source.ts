import { docs } from '@/.source/server';
import { loader } from 'fumadocs-core/source';
import { lucideIconsPlugin } from 'fumadocs-core/source/plugins/lucide-icons';

export const source = loader({
  baseUrl: '/docs',
  source: docs.toFumadocsSource(),
  // Lets meta.json files and page frontmatter name an icon, e.g. "Workflow".
  plugins: [lucideIconsPlugin()],
  pageTree: {
    transformers: [
      {
        // The page tree goes to the browser with every page. The ~850
        // integration pages' descriptions would add over 100 KB to each one,
        // and nothing in the sidebar shows them. Hand-written pages keep
        // theirs: the previous/next links at the foot of a page show them.
        file(node, filePath) {
          if (!filePath?.startsWith('integrations/')) return node;
          const { description: _description, ...rest } = node;
          return rest;
        },
      },
    ],
  },
});
