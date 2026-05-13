import { getMDXComponents } from '@/mdx-components';

jest.mock('fumadocs-ui/mdx', () => ({
  __esModule: true,
  default: {
    h1: 'fumadocs-h1',
    p: 'fumadocs-p',
    code: 'fumadocs-code',
  },
}));

describe('getMDXComponents', () => {
  it('returns the fumadocs default components when no overrides are passed', () => {
    const components = getMDXComponents();
    expect(components).toEqual({
      h1: 'fumadocs-h1',
      p: 'fumadocs-p',
      code: 'fumadocs-code',
    });
  });

  it('merges user-provided overrides on top of defaults', () => {
    const Custom = () => null;
    const components = getMDXComponents({ p: Custom });
    expect(components.p).toBe(Custom);
    expect(components.h1).toBe('fumadocs-h1');
    expect(components.code).toBe('fumadocs-code');
  });

  it('allows extending the component map with new entries', () => {
    const components = getMDXComponents({ Callout: 'callout-block' as never });
    expect(components.Callout).toBe('callout-block');
    // Defaults remain intact.
    expect(components.h1).toBe('fumadocs-h1');
  });

  it('treats an empty override object as no overrides', () => {
    expect(getMDXComponents({})).toEqual(getMDXComponents());
  });

  it('returns a fresh object each call (no shared reference with defaults)', () => {
    const a = getMDXComponents();
    const b = getMDXComponents();
    expect(a).not.toBe(b);
    // Mutating one must not leak into the next call.
    (a as Record<string, unknown>).h1 = 'mutated';
    expect(getMDXComponents().h1).toBe('fumadocs-h1');
  });
});
