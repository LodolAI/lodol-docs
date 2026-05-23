import Link from 'next/link';

function ZapIcon() {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/>
    </svg>
  );
}

function WorkflowIcon() {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M21 2v6h-6"/>
      <path d="M3 12a9 9 0 0 1 15-6.7L21 8"/>
      <path d="M3 22v-6h6"/>
      <path d="M21 12a9 9 0 0 1-15 6.7L3 16"/>
    </svg>
  );
}

function GridIcon() {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <rect x="2" y="2" width="9" height="9"/>
      <rect x="13" y="2" width="9" height="9"/>
      <rect x="13" y="13" width="9" height="9"/>
      <rect x="2" y="13" width="9" height="9"/>
    </svg>
  );
}

function LockIcon() {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <rect x="3" y="11" width="18" height="11" rx="2" ry="2"/>
      <path d="M7 11V7a5 5 0 0 1 10 0v4"/>
    </svg>
  );
}

function PlayIcon() {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <polygon points="5 3 19 12 5 21 5 3"/>
    </svg>
  );
}

function ShieldIcon() {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>
    </svg>
  );
}

interface FeatureCardProps {
  title: string;
  description: string;
  href: string;
  icon: React.ReactNode;
}

function FeatureCard({ title, description, href, icon }: FeatureCardProps) {
  return (
    <Link
      href={href}
      className="flex flex-col gap-3 rounded-lg border border-fd-border p-6 hover:bg-fd-accent hover:text-fd-accent-foreground transition-colors"
    >
      <div className="flex items-center gap-3">
        <div className="text-fd-primary">{icon}</div>
        <h3 className="font-semibold">{title}</h3>
      </div>
      <p className="text-sm text-fd-muted-foreground">{description}</p>
    </Link>
  );
}

export default function HomePage() {
  return (
    <main className="flex flex-1 flex-col items-center px-4 py-16">
      <div className="text-center max-w-2xl mb-16">
        <h1 className="text-4xl font-bold mb-4 md:text-5xl">
          Lodol Developer API
        </h1>
        <p className="text-fd-muted-foreground mb-8 text-lg">
          Build powerful integrations with the Lodol API. Explore our guides,
          API reference, and examples to get started.
        </p>
        <div className="flex gap-4 justify-center">
          <Link
            href="/docs"
            className="inline-flex items-center justify-center rounded-md bg-fd-primary px-6 py-3 text-sm font-medium text-fd-primary-foreground shadow hover:bg-fd-primary/90 transition-colors"
          >
            Get Started
          </Link>
          <Link
            href="/docs/api-reference"
            className="inline-flex items-center justify-center rounded-md border border-fd-border px-6 py-3 text-sm font-medium hover:bg-fd-accent hover:text-fd-accent-foreground transition-colors"
          >
            API Reference
          </Link>
        </div>
      </div>

      <div className="w-full max-w-5xl">
        <h2 className="text-xl font-semibold mb-6">Explore the docs</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          <FeatureCard
            title="Quickstart"
            description="Get up and running with the Lodol API in minutes with a step-by-step guide."
            href="/docs/guides/quickstart"
            icon={<ZapIcon />}
          />
          <FeatureCard
            title="Workflows"
            description="Automate complex multi-step processes by connecting actions together in a workflow."
            href="/docs/api-reference/workflows"
            icon={<WorkflowIcon />}
          />
          <FeatureCard
            title="Integrations"
            description="Browse 200+ pre-built connections to popular apps and services."
            href="/docs/api-reference/actions"
            icon={<GridIcon />}
          />
          <FeatureCard
            title="Authentication"
            description="Learn how to authenticate your requests securely using API keys."
            href="/docs/guides/authentication"
            icon={<LockIcon />}
          />
          <FeatureCard
            title="Executions"
            description="Trigger and monitor workflow runs programmatically via the executions API."
            href="/docs/api-reference/executions"
            icon={<PlayIcon />}
          />
          <FeatureCard
            title="Error Handling"
            description="Understand API errors and learn how to build resilient integrations."
            href="/docs/guides/error-handling"
            icon={<ShieldIcon />}
          />
        </div>
      </div>
    </main>
  );
}
