import Link from 'next/link';
import type { ReactNode } from 'react';
import { ArrowRight, Blocks, BookOpen, Sparkles, Terminal } from 'lucide-react';
import { getCatalog } from '@/lib/catalog';
import { IntegrationIcon } from '@/components/integration-icon';
import { HomeSearch } from '@/components/home-search';

const STARTING_POINTS = [
  {
    title: 'Build with your AI tool',
    description:
      'Connect Claude, ChatGPT or Cursor to Lodol, describe the automation you want, and get a working workflow back.',
    href: '/docs/build-with-ai',
    icon: <Sparkles />,
  },
  {
    title: 'Learn how workflows work',
    description:
      'Triggers, steps, data and runs, explained with one real example from start to finish.',
    href: '/docs/concepts/workflows',
    icon: <BookOpen />,
  },
  {
    title: 'Run workflows from your code',
    description:
      'Start runs, pass in inputs and read results with the developer API, in about five minutes.',
    href: '/docs/api/quickstart',
    icon: <Terminal />,
  },
];

// The built-in steps the home page shows, in this order. The directory lists them all.
const FEATURED_STEPS = [
  'skipflow_agent',
  'skipflow_conditions',
  'skipflow_loops',
  'skipflow_review',
  'skipflow_schedule',
  'skipflow_files',
  'skipflow_text',
  'skipflow_http',
];

const GUIDES = [
  { title: 'Make decisions with If', href: '/docs/guides/conditions' },
  { title: 'Repeat steps for every item', href: '/docs/guides/loops' },
  { title: 'Ask for approval', href: '/docs/guides/approvals' },
  { title: 'Use an AI agent', href: '/docs/guides/ai-agents' },
  { title: 'Remember values between runs', href: '/docs/guides/stored-values' },
  { title: 'Run a workflow from another', href: '/docs/guides/sub-workflows' },
  { title: 'Handle failures', href: '/docs/guides/failures' },
  { title: 'Call an API or run code', href: '/docs/guides/http-and-code' },
];

const RESOURCES = [
  { title: 'Workflow templates', href: 'https://www.lodol.com/workflows' },
  { title: 'Changelog', href: 'https://www.lodol.com/changelog' },
  { title: 'Service status', href: 'https://status.lodol.com' },
  { title: 'Security & trust', href: 'https://trust.lodol.com' },
  { title: 'Community on Discord', href: 'https://discord.gg/GDpDdHwhZD' },
  { title: 'Contact support', href: 'https://www.lodol.com/contact' },
];

function SectionTitle({ children, action }: { children: ReactNode; action?: ReactNode }) {
  return (
    <div className="mb-5 flex items-end justify-between gap-4">
      <h2 className="text-xl font-semibold tracking-tight text-fd-foreground">{children}</h2>
      {action}
    </div>
  );
}

function MoreLink({ href, children }: { href: string; children: ReactNode }) {
  return (
    <Link
      href={href}
      className="group inline-flex items-center gap-1 text-sm font-medium text-fd-primary"
    >
      {children}
      <ArrowRight aria-hidden="true" className="size-4 transition-transform group-hover:translate-x-0.5" />
    </Link>
  );
}

export default function HomePage() {
  const catalog = getCatalog();
  const byId = new Map(catalog.entries.map((entry) => [entry.id, entry]));
  const steps = FEATURED_STEPS.flatMap((id) => byId.get(id) ?? []);
  const popular = catalog.popular.flatMap((id) => byId.get(id) ?? []).slice(0, 12);

  return (
    <main className="flex flex-1 flex-col">
      <section className="relative overflow-hidden border-b border-fd-border">
        <div
          aria-hidden="true"
          className="pointer-events-none absolute inset-x-0 -top-40 mx-auto h-[28rem] max-w-4xl rounded-full bg-[radial-gradient(closest-side,color-mix(in_oklab,var(--color-brand)_16%,transparent),transparent)] dark:bg-[radial-gradient(closest-side,color-mix(in_oklab,var(--color-brand)_28%,transparent),transparent)]"
        />
        <div className="relative mx-auto flex max-w-5xl flex-col items-center px-6 pb-20 pt-20 text-center md:pt-28">
          <p className="mb-5 text-xs font-semibold uppercase tracking-[0.18em] text-fd-primary">
            Lodol documentation
          </p>
          <h1 className="font-display text-[3.4rem] uppercase leading-[0.95] text-fd-foreground sm:text-7xl md:text-[5.5rem]">
            Build it once.
            <br />
            <span className="text-brand dark:text-brand-lilac">Lodol runs it every time.</span>
          </h1>
          <p className="mt-6 max-w-xl text-lg leading-relaxed text-fd-muted-foreground">
            Learn how workflows start, what every step can do, and how to run them from your
            own code.
          </p>
          <div className="mt-9 flex w-full justify-center">
            <HomeSearch />
          </div>
        </div>
      </section>

      <div className="mx-auto w-full max-w-6xl px-6 py-16">
        <section aria-labelledby="start-here">
          <h2 id="start-here" className="sr-only">
            Start here
          </h2>
          <div className="grid gap-4 md:grid-cols-3">
            {STARTING_POINTS.map((point) => (
              <Link
                key={point.href}
                href={point.href}
                className="group flex flex-col rounded-2xl border border-fd-border bg-fd-card p-6 transition-all hover:-translate-y-0.5 hover:border-fd-primary/40 hover:shadow-[0_12px_32px_-12px_color-mix(in_oklab,var(--color-brand)_30%,transparent)]"
              >
                <span className="mb-5 inline-flex size-10 items-center justify-center rounded-xl bg-brand-soft text-brand dark:bg-brand/20 dark:text-brand-lilac [&_svg]:size-5">
                  {point.icon}
                </span>
                <span className="text-base font-semibold text-fd-foreground">{point.title}</span>
                <span className="mt-2 flex-1 text-sm leading-relaxed text-fd-muted-foreground">
                  {point.description}
                </span>
                <span className="mt-5 inline-flex items-center gap-1 text-sm font-medium text-fd-primary">
                  Start
                  <ArrowRight aria-hidden="true" className="size-4 transition-transform group-hover:translate-x-0.5" />
                </span>
              </Link>
            ))}
          </div>
        </section>

        <section aria-labelledby="built-in-steps" className="mt-20">
          <SectionTitle
            action={<MoreLink href="/docs/integrations#built-in-steps">All built-in steps</MoreLink>}
          >
            <span id="built-in-steps">The steps every workflow is made of</span>
          </SectionTitle>
          <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
            {steps.map((step) => (
              <Link
                key={step.id}
                href={step.href}
                className="flex items-center gap-3 rounded-xl border border-fd-border bg-fd-card/60 p-3 transition-colors hover:border-fd-primary/40 hover:bg-fd-accent/40"
              >
                <IntegrationIcon name={step.name} icon={step.icon} builtIn size="sm" />
                <span className="min-w-0 truncate text-sm font-medium text-fd-foreground">{step.name}</span>
              </Link>
            ))}
          </div>
        </section>

        <section aria-labelledby="integrations" className="mt-20">
          <div className="grid gap-10 rounded-3xl border border-fd-border bg-fd-card p-8 md:grid-cols-[1fr_1.4fr] md:p-10">
            <div>
              <span className="inline-flex size-10 items-center justify-center rounded-xl bg-brand-soft text-brand dark:bg-brand/20 dark:text-brand-lilac">
                <Blocks aria-hidden="true" className="size-5" />
              </span>
              <h2 id="integrations" className="mt-5 text-2xl font-semibold tracking-tight text-fd-foreground">
                {catalog.apps} apps, {catalog.appActions.toLocaleString('en-US')} actions
              </h2>
              <p className="mt-3 text-sm leading-relaxed text-fd-muted-foreground">
                Every action documented with its inputs, its outputs and an example of what it
                returns. Anything else with an API is one Call an API step away.
              </p>
              <div className="mt-6">
                <MoreLink href="/docs/integrations">Browse integrations</MoreLink>
              </div>
            </div>
            <ul className="grid grid-cols-2 gap-2.5 sm:grid-cols-3">
              {popular.map((app) => (
                <li key={app.id}>
                  <Link
                    href={app.href}
                    className="flex items-center gap-2.5 rounded-xl border border-fd-border bg-fd-background/60 p-2.5 transition-colors hover:border-fd-primary/40"
                  >
                    <IntegrationIcon name={app.name} size="sm" />
                    <span className="min-w-0 truncate text-sm font-medium text-fd-foreground">{app.name}</span>
                  </Link>
                </li>
              ))}
            </ul>
          </div>
        </section>

        <section className="mt-20 grid gap-12 md:grid-cols-2">
          <div>
            <SectionTitle>Guides</SectionTitle>
            <ul className="divide-y divide-fd-border rounded-2xl border border-fd-border">
              {GUIDES.map((guide) => (
                <li key={guide.href}>
                  <Link
                    href={guide.href}
                    className="group flex items-center justify-between px-5 py-3.5 text-sm font-medium text-fd-foreground transition-colors hover:text-fd-primary"
                  >
                    {guide.title}
                    <ArrowRight aria-hidden="true" className="size-4 text-fd-muted-foreground transition-transform group-hover:translate-x-0.5 group-hover:text-fd-primary" />
                  </Link>
                </li>
              ))}
            </ul>
          </div>
          <div>
            <SectionTitle>Resources</SectionTitle>
            <ul className="divide-y divide-fd-border rounded-2xl border border-fd-border">
              {RESOURCES.map((resource) => (
                <li key={resource.href}>
                  <a
                    href={resource.href}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="group flex items-center justify-between px-5 py-3.5 text-sm font-medium text-fd-foreground transition-colors hover:text-fd-primary"
                  >
                    {resource.title}
                    <span aria-hidden="true" className="text-fd-muted-foreground group-hover:text-fd-primary">↗</span>
                  </a>
                </li>
              ))}
            </ul>
          </div>
        </section>
      </div>
    </main>
  );
}
