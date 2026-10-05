import type { ComponentProps, ReactElement } from 'react';
import { highlight } from 'fumadocs-core/highlight';
import { getMDXComponents } from '@/mdx-components';

jest.mock('fumadocs-ui/mdx', () => ({
  __esModule: true,
  default: {
    h1: 'fumadocs-h1',
    p: 'fumadocs-p',
    code: 'fumadocs-code',
    pre: 'fumadocs-pre',
  },
}));

jest.mock('fumadocs-core/highlight', () => ({
  highlight: jest.fn(async () => 'highlighted code'),
}));

describe('getMDXComponents', () => {
  it('returns the fumadocs default components, with its own pre, when no overrides are passed', () => {
    const components = getMDXComponents();
    expect(components).toEqual({
      h1: 'fumadocs-h1',
      p: 'fumadocs-p',
      code: 'fumadocs-code',
      pre: expect.any(Function),
    });
  });

  it('merges user-provided overrides on top of defaults', () => {
    const Custom = () => null;
    const components = getMDXComponents({ p: Custom, pre: Custom });
    expect(components.p).toBe(Custom);
    expect(components.pre).toBe(Custom);
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

describe('pre', () => {
  const Pre = getMDXComponents().pre as (
    props: ComponentProps<'pre'>,
  ) => ReactElement<Record<string, unknown>>;

  // What React does with the element Pre returns, on the server.
  function render(element: ReactElement<Record<string, unknown>>) {
    return (element.type as (props: unknown) => unknown)(element.props);
  }

  beforeEach(() => jest.mocked(highlight).mockClear());

  it('passes a code block the build highlighted to the fumadocs pre as is', () => {
    const code = (
      <code>
        <span className="line">{'{}'}</span>
      </code>
    );
    const element = Pre({ className: 'shiki', children: code });
    expect(element.type).toBe('fumadocs-pre');
    expect(element.props).toEqual({ className: 'shiki', children: code });
    expect(highlight).not.toHaveBeenCalled();
  });

  it('highlights a plain code block in its language as the page renders', async () => {
    const element = Pre({
      children: <code className="language-json">{'{\n  "ok": true\n}\n'}</code>,
    });
    await expect(render(element)).resolves.toBe('highlighted code');
    expect(highlight).toHaveBeenCalledWith('{\n  "ok": true\n}', {
      lang: 'json',
      components: { pre: 'fumadocs-pre' },
    });
  });

  it('highlights a plain code block with no language as plain text', async () => {
    await render(Pre({ children: <code>{'just text\n'}</code> }));
    expect(highlight).toHaveBeenCalledWith('just text', {
      lang: 'plaintext',
      components: { pre: 'fumadocs-pre' },
    });
  });
});
