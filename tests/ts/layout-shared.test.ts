import { baseOptions } from '@/lib/layout.shared';

describe('baseOptions', () => {
  it('returns the expected nav title for the docs site', () => {
    const opts = baseOptions();
    expect(opts.nav).toBeDefined();
    expect(opts.nav?.title).toBe('Lodol Docs');
  });

  it('exposes a link to the API Reference section', () => {
    const opts = baseOptions();
    expect(Array.isArray(opts.links)).toBe(true);
    expect(opts.links).toHaveLength(1);
    const link = opts.links?.[0];
    expect(link).toMatchObject({
      text: 'API Reference',
      url: '/docs/api-reference',
    });
  });

  it('returns a fresh options object on every call', () => {
    // The shared options are consumed by layout components which may
    // mutate the returned object during rendering. Returning a fresh
    // object each time avoids cross-request bleed in server rendering.
    const a = baseOptions();
    const b = baseOptions();
    expect(a).not.toBe(b);
    expect(a.links).not.toBe(b.links);
  });

  it('API Reference link points to an internal docs path', () => {
    const link = baseOptions().links?.[0] as { url?: string } | undefined;
    const url = link?.url ?? '';
    expect(typeof url).toBe('string');
    expect(url.startsWith('/')).toBe(true);
    expect(url).not.toMatch(/^https?:/);
  });
});
