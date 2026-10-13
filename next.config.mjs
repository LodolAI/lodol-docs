import { createMDX } from 'fumadocs-mdx/next';

const withMDX = createMDX();

/** @type {import('next').NextConfig} */
const config = {
  reactStrictMode: true,
  output: 'standalone',
  // Pages that moved when the docs were reorganized into Documentation,
  // Integrations and API. Links to the old addresses keep working.
  async redirects() {
    return [
      { source: '/docs/guides/quickstart', destination: '/docs/api/quickstart', permanent: true },
      { source: '/docs/guides/authentication', destination: '/docs/api/authentication', permanent: true },
      { source: '/docs/guides/error-handling', destination: '/docs/api/errors', permanent: true },
      { source: '/docs/api-reference', destination: '/docs/api', permanent: true },
      { source: '/docs/api-reference/workflows', destination: '/docs/api/workflows', permanent: true },
      { source: '/docs/api-reference/executions', destination: '/docs/api/runs', permanent: true },
      { source: '/docs/api-reference/core', destination: '/docs/api/workflow-format', permanent: true },
      { source: '/docs/api-reference/core/:page', destination: '/docs/api/workflow-format', permanent: true },
      { source: '/docs/api-reference/actions', destination: '/docs/integrations', permanent: true },
      // Lodol's own steps were published as skipflow-* providers.
      {
        source: '/docs/api-reference/actions/skipflow-:step',
        destination: '/docs/integrations/built-in/:step',
        permanent: true,
      },
      { source: '/docs/api-reference/actions/:app', destination: '/docs/integrations/:app', permanent: true },
    ];
  },
};

export default withMDX(config);
