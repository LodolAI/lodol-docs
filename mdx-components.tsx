import defaultMdxComponents from 'fumadocs-ui/mdx';
import { highlight } from 'fumadocs-core/highlight';
import { Step, Steps } from 'fumadocs-ui/components/steps';
import { Tab, Tabs } from 'fumadocs-ui/components/tabs';
import { Accordion, Accordions } from 'fumadocs-ui/components/accordion';
import { isValidElement, type ComponentProps } from 'react';
import type { MDXComponents } from 'mdx/types';
import { Endpoint, Example, Field, Fields } from '@/components/reference';
import { IntegrationDirectory } from '@/components/integration-directory';
import { AppsWithTriggers } from '@/components/apps-with-triggers';
import { WorkflowPreview } from '@/components/workflow-preview';

const DefaultPre = defaultMdxComponents.pre;

async function HighlightedCode({ code, lang }: { code: string; lang: string }) {
  return highlight(code, { lang, components: { pre: DefaultPre } });
}

/**
 * A code block. Code arrives highlighted from the build, except the
 * integration reference's (see lib/rehype-code.ts), which arrives as plain
 * text and is highlighted here as its page renders, with the same themes and
 * `pre`.
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
    Steps,
    Step,
    Tabs,
    Tab,
    Accordions,
    Accordion,
    Fields,
    Field,
    Example,
    Endpoint,
    IntegrationDirectory,
    AppsWithTriggers,
    WorkflowPreview,
    ...components,
  };
}
