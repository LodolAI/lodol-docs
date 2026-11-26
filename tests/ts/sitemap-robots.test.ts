jest.mock('@/lib/source', () => ({
  source: {
    getPages: () => [{ url: '/docs' }, { url: '/docs/integrations/slack' }, { url: '/docs/api/quickstart' }],
  },
}));

import sitemap, { SITE } from '@/app/sitemap';
import robots from '@/app/robots';

describe('sitemap', () => {
  it('lists the home page and every docs page at its full address', () => {
    expect(sitemap().map((entry) => entry.url)).toEqual([
      'https://docs.lodol.com/',
      'https://docs.lodol.com/docs',
      'https://docs.lodol.com/docs/integrations/slack',
      'https://docs.lodol.com/docs/api/quickstart',
    ]);
  });
});

describe('robots', () => {
  it('lets every crawler read the docs, keeps it out of the API and points to the sitemap', () => {
    const { rules, sitemap: map } = robots();
    expect(rules).toEqual([{ userAgent: '*', allow: '/', disallow: '/api/' }]);
    expect(map).toBe(`${SITE}/sitemap.xml`);
  });
});
