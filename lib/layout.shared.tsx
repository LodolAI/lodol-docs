import type { BaseLayoutProps } from 'fumadocs-ui/layouts/shared';

export function baseOptions(): BaseLayoutProps {
  return {
    nav: {
      title: 'Lodol Docs',
    },
    links: [
      {
        text: 'API Reference',
        url: '/docs/api-reference',
      },
    ],
  };
}
