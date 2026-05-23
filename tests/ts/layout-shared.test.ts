import { baseOptions } from '@/lib/layout.shared';

describe('baseOptions', () => {
  it('returns the expected nav title for the docs site', () => {
    const opts = baseOptions();
    expect(opts.nav).toBeDefined();
    expect(opts.nav?.title).toBe('Lodol Docs');
  });

  it('does not add extra navigation links above the page tree', () => {
    const opts = baseOptions();
    expect(!opts.links || (opts.links as unknown[]).length === 0).toBe(true);
  });

  it('returns a fresh options object on every call', () => {
    // The shared options are consumed by layout components which may
    // mutate the returned object during rendering. Returning a fresh
    // object each time avoids cross-request bleed in server rendering.
    const a = baseOptions();
    const b = baseOptions();
    expect(a).not.toBe(b);
  });
});
