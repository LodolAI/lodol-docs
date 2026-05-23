import { baseOptions } from '@/lib/layout.shared';

describe('baseOptions', () => {
  it('returns the expected nav title for the docs site', () => {
    const opts = baseOptions();
    expect(opts.nav).toBeDefined();
    expect(opts.nav?.title).toBe('Lodol Docs');
  });

  it('has a website button linking to skipflow.com in the topbar', () => {
    const opts = baseOptions();
    const links = (opts.links ?? []) as Array<{ url?: string; external?: boolean; on?: string }>;
    const websiteLink = links.find(l => l.url === 'https://www.skipflow.com/');
    expect(websiteLink).toBeDefined();
    expect(websiteLink?.external).toBe(true);
    expect(websiteLink?.on).toBe('nav');
  });

  it('has a GitHub icon button linking to the docs repo in the topbar', () => {
    const opts = baseOptions();
    const links = (opts.links ?? []) as Array<{ type?: string; url?: string; external?: boolean; on?: string }>;
    const githubLink = links.find(l => l.url === 'https://github.com/LodolAI/lodol-docs');
    expect(githubLink).toBeDefined();
    expect(githubLink?.type).toBe('icon');
    expect(githubLink?.external).toBe(true);
    expect(githubLink?.on).toBe('nav');
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
