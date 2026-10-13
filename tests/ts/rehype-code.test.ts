import { rehypeCodeOutsideIntegrationReference } from '@/lib/rehype-code';

const mockHighlight = jest.fn();

jest.mock('fumadocs-core/mdx-plugins', () => ({
  rehypeCode: () => mockHighlight,
}));

function transform(path: string) {
  const transformer = rehypeCodeOutsideIntegrationReference.call({} as never);
  const tree = { type: 'root' as const, children: [] };
  const file = { path } as never;
  return { result: transformer(tree, file, () => {}), tree, file };
}

describe('rehypeCodeOutsideIntegrationReference', () => {
  beforeEach(() => mockHighlight.mockReset());

  it.each([
    '/repo/content/docs/api/quickstart.mdx',
    '/repo/content/docs/(docs)/guides/approvals.mdx',
    '/repo/content/docs/api/runs.mdx',
  ])('highlights the code on %s as the page compiles', (path) => {
    mockHighlight.mockResolvedValue(undefined);
    const { result, tree, file } = transform(path);
    expect(mockHighlight).toHaveBeenCalledWith(tree, file, expect.any(Function));
    expect(result).toBe(mockHighlight.mock.results[0].value);
  });

  it.each([
    '/repo/content/docs/integrations/slack.mdx',
    '/repo/content/docs/integrations/index.mdx',
    '/repo/content/docs/integrations/built-in/review.mdx',
    'C:\\repo\\content\\docs\\integrations\\slack.mdx',
  ])('leaves the code on %s for the page to highlight as it renders', (path) => {
    const { result } = transform(path);
    expect(result).toBeUndefined();
    expect(mockHighlight).not.toHaveBeenCalled();
  });

  it('takes no `next`, so unified waits on the promise it returns', () => {
    // unified hands a transformer that declares a third parameter a callback
    // and waits for it to be called, which this transformer never does.
    expect(rehypeCodeOutsideIntegrationReference.call({} as never)).toHaveLength(2);
  });
});
