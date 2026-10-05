import defaultMdxComponents from 'fumadocs-ui/mdx';
import { highlight } from 'fumadocs-core/highlight';
import { isValidElement, type ComponentProps } from 'react';
import type { MDXComponents } from 'mdx/types';

const DefaultPre = defaultMdxComponents.pre;

async function HighlightedCode({ code, lang }: { code: string; lang: string }) {
  return highlight(code, { lang, components: { pre: DefaultPre } });
}

/**
 * A code block. Code arrives highlighted from the build, except the action
 * reference's (see lib/rehype-code.ts), which arrives as plain text and is
 * highlighted here as its page renders, with the same themes and `pre`.
 */
function Pre(props: ComponentProps<'pre'>) {
  const code = props.children;
  if (
    isValidElement<ComponentProps<'code'>>(code) &&
    typeof code.props.children === 'string'
  ) {
    const lang = /language-(\S+)/.exec(code.props.className ?? '')?.[1];
    return (
      <HighlightedCode
        code={code.props.children.replace(/\n$/, '')}
        lang={lang ?? 'plaintext'}
      />
    );
  }
  return <DefaultPre {...props} />;
}

export function getMDXComponents(components?: MDXComponents): MDXComponents {
  return {
    ...defaultMdxComponents,
    pre: Pre,
    ...components,
  };
}
