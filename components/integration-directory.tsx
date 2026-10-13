import { getCatalog } from '@/lib/catalog';
import { IntegrationIcon } from '@/components/integration-icon';
import { DirectoryBrowser, type DirectoryItem } from '@/components/directory-browser';

/**
 * Every app and built-in step, searchable. Built-in steps' icons are drawn
 * here, on the server; apps' initials are cheap enough to draw in the browser.
 */
export function IntegrationDirectory() {
  const catalog = getCatalog();
  const items: DirectoryItem[] = catalog.entries.map((entry) => ({
    id: entry.id,
    name: entry.name,
    description: entry.description,
    href: entry.href,
    actions: entry.actions,
    builtIn: entry.builtIn,
    icon: entry.builtIn ? (
      <IntegrationIcon name={entry.name} icon={entry.icon} builtIn size="sm" />
    ) : undefined,
  }));
  return (
    <DirectoryBrowser
      items={items}
      popular={catalog.popular}
      apps={catalog.apps}
    />
  );
}
