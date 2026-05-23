import type { BaseLayoutProps } from 'fumadocs-ui/layouts/shared';

export function baseOptions(): BaseLayoutProps {
  return {
    nav: {
      title: 'Lodol Docs',
    },
    githubUrl: 'https://github.com/LodolAI/lodol-docs',
    links: [
      {
        type: 'button',
        text: 'skipflow.com',
        url: 'https://www.skipflow.com/',
        external: true,
      },
    ],
  };
}
