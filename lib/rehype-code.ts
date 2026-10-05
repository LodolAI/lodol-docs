import { rehypeCode } from 'fumadocs-core/mdx-plugins';

type Processor = ThisParameterType<typeof rehypeCode>;
type Transformer = ReturnType<typeof rehypeCode>;

/**
 * The pages scripts/render-actions-docs.py generates, one per provider.
 */
const ACTION_REFERENCE_PAGE =
  /[\\/]content[\\/]docs[\\/]api-reference[\\/]actions[\\/]/;

/**
 * fumadocs' code highlighting, for every page but the action reference's.
 *
 * Highlighting as the pages compile turns each token of code into its own
 * element, which makes a compiled page two to three times the size. The
 * action reference holds over 9,000 JSON examples, and highlighting them took
 * the production build past the 16 GB its runner has. Its code blocks compile as plain text
 * and are highlighted as each page renders, by `pre` in mdx-components.tsx.
 */
export function rehypeCodeOutsideActionReference(
  this: Processor,
): Transformer {
  const highlight = rehypeCode.call(this);
  // Two parameters, not three: unified waits for a transformer that takes
  // `next` to call it, and rehypeCode's returns a promise instead.
  return (tree, file) => {
    if (ACTION_REFERENCE_PAGE.test(file.path)) return;
    return highlight(tree, file, () => {});
  };
}
