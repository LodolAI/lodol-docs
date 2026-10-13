import { isValidElement } from 'react';
import { baseOptions, APP_URL, GITHUB_URL, NavTitle } from '@/lib/layout.shared';

jest.mock('@/components/logo', () => ({ LodolLogo: () => null }));

type Link = {
  type?: string;
  text?: unknown;
  url?: string;
  external?: boolean;
  on?: string;
  label?: string;
};

describe('baseOptions', () => {
  it('shows the Lodol Docs lockup as the nav title, linking home', () => {
    const opts = baseOptions();
    expect(isValidElement(opts.nav?.title)).toBe(true);
    expect((opts.nav?.title as { type: unknown }).type).toBe(NavTitle);
    expect(opts.nav?.url).toBe('/');
  });

  it('links to the Lodol app from the navbar', () => {
    const links = (baseOptions().links ?? []) as Link[];
    const app = links.find((l) => l.url === APP_URL);
    expect(APP_URL).toBe('https://app.lodol.com');
    expect(app).toMatchObject({ text: 'Open Lodol', external: true, on: 'nav' });
  });

  it('has a GitHub icon button linking to the docs repo in the navbar', () => {
    const links = (baseOptions().links ?? []) as Link[];
    const github = links.find((l) => l.url === GITHUB_URL);
    expect(GITHUB_URL).toBe('https://github.com/LodolAI/lodol-docs');
    expect(github).toMatchObject({ type: 'icon', external: true, on: 'nav' });
    expect(github?.label).toBeTruthy();
  });

  it('no longer links to the old Skipflow website', () => {
    const links = (baseOptions().links ?? []) as Link[];
    expect(JSON.stringify(links.map((l) => l.url))).not.toContain('skipflow');
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
