import { baseOptions } from '@/lib/layout.shared';

describe('baseOptions', () => {
  it('returns the expected nav title for the docs site', () => {
    const opts = baseOptions();
    expect(opts.nav).toBeDefined();
    expect(opts.nav?.title).toBe('Lodol Docs');
  });

  it('has a custom secondary website link in the topbar', () => {
    const opts = baseOptions();
    const links = (opts.links ?? []) as Array<{ type?: string; secondary?: boolean; on?: string }>;
    const websiteLink = links.find(l => l.type === 'custom' && l.secondary === true);
    expect(websiteLink).toBeDefined();
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

  it('renders the GitHub icon button before the website link so website appears to the right', () => {
    const opts = baseOptions();
    const links = (opts.links ?? []) as Array<{ type?: string; url?: string }>;
    const githubIndex = links.findIndex(l => l.url === 'https://github.com/LodolAI/lodol-docs');
    const websiteIndex = links.findIndex(l => l.type === 'custom');
    expect(githubIndex).toBeGreaterThanOrEqual(0);
    expect(websiteIndex).toBeGreaterThan(githubIndex);
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
