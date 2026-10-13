import Link from 'next/link';
import { getCatalog } from '@/lib/catalog';
import { IntegrationIcon } from '@/components/integration-icon';

/** Every app with triggers, each linking to the triggers on its page. */
export function AppsWithTriggers() {
  const apps = getCatalog().entries.filter((entry) => !entry.builtIn && entry.triggers);
  return (
    <ul className="not-prose my-6 grid grid-cols-2 gap-2 sm:grid-cols-3">
      {apps.map((app) => (
        <li key={app.id}>
          <Link
            href={`${app.href}#triggers`}
            className="flex items-center gap-2.5 rounded-xl border border-fd-border p-2 text-sm font-medium text-fd-foreground transition-colors hover:border-fd-primary/40 hover:bg-fd-accent/40"
          >
            <IntegrationIcon name={app.name} logo={app.logo} size="sm" />
            <span className="min-w-0 truncate">{app.name}</span>
          </Link>
        </li>
      ))}
    </ul>
  );
}
