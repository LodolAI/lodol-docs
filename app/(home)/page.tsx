import Link from 'next/link';
import type { ReactNode } from 'react';
import { ArrowRight, ArrowUpRight, Blocks, Check } from 'lucide-react';
import { getCatalog } from '@/lib/catalog';
import { IntegrationIcon } from '@/components/integration-icon';
import { HomeSearch } from '@/components/home-search';
import { CopyLine } from '@/components/copy-line';

// Connecting, as /docs/build-with-ai has it: the server URL, the one-line
// Claude Code command, and the links that open Claude and Cursor with Lodol
// filled in.
const MCP_URL = 'https://mcp.lodol.com/mcp';
const CLAUDE_CODE = `claude mcp add --transport http lodol ${MCP_URL}`;
const ADD_TO = [
  {
    name: 'Claude',
    href: 'https://claude.ai/customize/connectors?modal=add-custom-connector&connectorName=Lodol&connectorUrl=https%3A%2F%2Fmcp.lodol.com%2Fmcp',
  },
  {
    name: 'Cursor',
    href: 'https://cursor.com/install-mcp?name=lodol&config=eyJ1cmwiOiJodHRwczovL21jcC5sb2RvbC5jb20vbWNwIn0%3D',
  },
];

// The three ways in, each with a picture of the page it opens: the request
// /docs/build-with-ai suggests, the workflow /docs/concepts/workflows
// explains, and the call /docs/api/quickstart makes.
const ASK = 'Use Lodol: when a Stripe payment comes in, add it to our revenue sheet and post it in #sales.';
const EXAMPLE_STEPS = [
  { step: 'New Stripe payment', app: 'Stripe', trigger: true },
  { step: 'Append row', app: 'Google Sheets' },
  { step: 'Send a message to a channel', app: 'Slack' },
];
const RUN_CALL = [
  'API=https://api-prod.lodol.com/api/v1',
  'curl -X POST $API/workflows/$ID/run-async \\',
  '  -H "Authorization: Bearer $LODOL_API_KEY"',
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

function AskPicture() {
  return (
    <div className="flex w-full max-w-[19rem] flex-col gap-2.5">
      <p className="self-end rounded-2xl rounded-br-md border border-fd-border bg-fd-background px-3.5 py-2.5 text-[13px] leading-snug text-fd-foreground">
        {ASK}
      </p>
      <p className="inline-flex items-center gap-2 self-start rounded-lg border border-fd-border bg-fd-background px-2.5 py-1.5 text-xs text-fd-muted-foreground">
        Created <span className="font-medium text-fd-foreground">Log Stripe payments</span>
        <Check aria-hidden="true" className="size-3.5 text-emerald-600" />
      </p>
    </div>
  );
}

function WorkflowPicture({ logos }: { logos: Map<string, string | undefined> }) {
  return (
    <ol className="flex w-full max-w-[17rem] flex-col">
      {EXAMPLE_STEPS.map((step, i) => (
        <li key={step.step}>
          {i > 0 && <div aria-hidden="true" className="ml-[1.1rem] h-2 w-px bg-fd-primary/40" />}
          <div
            className={`flex items-center gap-2.5 rounded-lg border bg-fd-background px-2 py-1 ${step.trigger ? 'border-fd-primary/40' : 'border-fd-border'}`}
          >
            <IntegrationIcon name={step.app} logo={logos.get(step.app)} size="sm" />
            <span className="min-w-0 flex-1 truncate text-xs font-medium text-fd-foreground">{step.step}</span>
            {step.trigger && (
              <span className="rounded-full bg-brand-soft px-1.5 py-0.5 text-[10px] font-medium text-brand-strong dark:bg-brand/20 dark:text-brand-lilac">
                Trigger
              </span>
            )}
          </div>
        </li>
      ))}
    </ol>
  );
}

function CodePicture() {
  return (
    <pre className="w-full max-w-[21rem] overflow-hidden rounded-lg border border-white/10 bg-[#16141f] px-3.5 py-3 font-mono text-[11px] leading-[1.6] text-[#d8d4e6] dark:bg-[#0a0910]">
      {RUN_CALL.map((line) => (
        <span key={line} className="block whitespace-pre">
          {line}
        </span>
      ))}
    </pre>
  );
}

const startingPoints = (logos: Map<string, string | undefined>) => [
  {
    title: 'Build with your AI tool',
    description: 'Describe the automation you want, and get a working workflow back.',
    href: '/docs/build-with-ai',
    picture: <AskPicture />,
  },
  {
    title: 'Learn how workflows work',
    description: 'Triggers, steps, data and runs, through one real example.',
    href: '/docs/concepts/workflows',
    picture: <WorkflowPicture logos={logos} />,
  },
  {
    title: 'Run workflows from your code',
    description: 'Start runs and read their results with the API, in about five minutes.',
    href: '/docs/api/quickstart',
    picture: <CodePicture />,
  },
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
  const logos = new Map(catalog.entries.map((entry) => [entry.name, entry.logo]));

  return (
    <main className="flex flex-1 flex-col">
      <section className="relative overflow-hidden border-b border-fd-border">
        <div
          aria-hidden="true"
          className="pointer-events-none absolute -top-32 left-0 h-[24rem] w-[40rem] rounded-full bg-[radial-gradient(closest-side,color-mix(in_oklab,var(--color-brand)_12%,transparent),transparent)] dark:bg-[radial-gradient(closest-side,color-mix(in_oklab,var(--color-brand)_24%,transparent),transparent)]"
        />
        <div className="relative mx-auto grid max-w-6xl items-center gap-10 px-6 pb-14 pt-14 md:grid-cols-[1.15fr_1fr] md:pt-20">
          {/* min-w-0 on both: the command below doesn't wrap, and without it the
              column grows to fit it on a phone and the section clips the rest. */}
          <div className="min-w-0">
            <p className="mb-5 inline-flex rounded-lg border border-fd-border bg-fd-background px-2.5 py-1 text-[13px] font-medium text-fd-muted-foreground shadow-sm">
              Documentation
            </p>
            <h1 className="font-display text-[2.9rem] uppercase leading-[0.95] text-fd-foreground sm:text-6xl">
              Your AI builds it.
              <br />
              <span className="text-brand dark:text-brand-lilac">Lodol runs it.</span>
            </h1>
            <p className="mt-5 max-w-lg text-[17px] leading-relaxed text-fd-muted-foreground">
              Connect your AI tool, learn how workflows run, and look up every app and step.
            </p>
            <div className="mt-7 flex">
              <HomeSearch />
            </div>
          </div>

          <section
            aria-labelledby="connect-title"
            className="min-w-0 rounded-2xl border border-fd-border bg-fd-card p-5 shadow-[0_12px_32px_-16px_color-mix(in_oklab,var(--color-brand)_28%,transparent)] sm:p-6"
          >
            <h2 id="connect-title" className="text-base font-semibold text-fd-foreground">
              Connect your AI tool
            </h2>
            <p className="mt-1 text-sm text-fd-muted-foreground">
              Sign in with your Lodol account when it asks. There&apos;s no key to copy.
            </p>
            <div className="mt-4 flex flex-wrap gap-2">
              {ADD_TO.map((tool) => (
                <a
                  key={tool.name}
                  href={tool.href}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-1.5 rounded-lg bg-fd-primary px-3 py-1.5 text-sm font-medium text-fd-primary-foreground transition-colors hover:bg-brand-strong"
                >
                  Add to {tool.name}
                  <ArrowUpRight aria-hidden="true" className="size-3.5" />
                </a>
              ))}
            </div>
            <div className="mt-5 space-y-3.5">
              <CopyLine label="Claude Code" value={CLAUDE_CODE} />
              <CopyLine label="Any other MCP tool" value={MCP_URL} />
            </div>
            <div className="mt-4">
              <MoreLink href="/docs/build-with-ai">ChatGPT, VS Code and other tools</MoreLink>
            </div>
          </section>
        </div>
      </section>

      <div className="mx-auto w-full max-w-6xl px-6 py-16">
        <section aria-labelledby="start-here">
          <h2 id="start-here" className="sr-only">
            Start here
          </h2>
          <div className="grid gap-4 md:grid-cols-3">
            {startingPoints(logos).map((point) => (
              <Link
                key={point.href}
                href={point.href}
                className="group flex flex-col overflow-hidden rounded-2xl border border-fd-border bg-fd-card transition-all hover:-translate-y-0.5 hover:border-fd-primary/40 hover:shadow-[0_12px_32px_-12px_color-mix(in_oklab,var(--color-brand)_30%,transparent)]"
              >
                <div
                  aria-hidden="true"
                  className="flex h-48 items-center justify-center border-b border-fd-border bg-fd-muted bg-[radial-gradient(circle_at_1px_1px,color-mix(in_oklab,var(--color-fd-foreground)_9%,transparent)_1px,transparent_0)] bg-[size:16px_16px] px-5"
                >
                  {point.picture}
                </div>
                <div className="flex flex-1 flex-col p-5">
                  <span className="text-base font-semibold text-fd-foreground">{point.title}</span>
                  <span className="mt-1.5 flex-1 text-sm leading-relaxed text-fd-muted-foreground">
                    {point.description}
                  </span>
                  <span className="mt-4 inline-flex items-center gap-1 text-sm font-medium text-fd-primary">
                    Start
                    <ArrowRight aria-hidden="true" className="size-4 transition-transform group-hover:translate-x-0.5" />
                  </span>
                </div>
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
                    <IntegrationIcon name={app.name} logo={app.logo} size="sm" />
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
