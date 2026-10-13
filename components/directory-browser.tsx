'use client';

import { useDeferredValue, useMemo, useState, type ReactNode } from 'react';
import Link from 'next/link';
import { Search, X } from 'lucide-react';
import { AppMonogram } from '@/components/app-monogram';

export interface DirectoryItem {
  id: string;
  name: string;
  description: string;
  href: string;
  actions: number;
  builtIn: boolean;
  /** Drawn on the server for built-in steps; apps get their initials. */
  icon?: ReactNode;
}

interface DirectoryBrowserProps {
  items: DirectoryItem[];
  popular: string[];
  apps: number;
}

/** Lower case without accents, so "notificación" finds "notificacion". */
function normalize(text: string): string {
  return text.normalize('NFD').replace(/\p{M}/gu, '').toLowerCase();
}

function countLabel(item: DirectoryItem): string {
  const noun = item.builtIn ? 'step' : 'action';
  return `${item.actions} ${noun}${item.actions === 1 ? '' : 's'}`;
}

function search(items: DirectoryItem[], query: string): DirectoryItem[] {
  const q = normalize(query.trim());
  const terms = q.split(/\s+/).filter(Boolean);
  const ranked: Array<[number, DirectoryItem]> = [];
  for (const item of items) {
    const name = normalize(item.name);
    const text = `${name} ${normalize(item.description)}`;
    if (!terms.every((term) => text.includes(term))) continue;
    // Name matches first, best first; then matches in the description.
    const rank = name === q ? 0 : name.startsWith(q) ? 1 : name.includes(q) ? 2 : 3;
    ranked.push([rank, item]);
  }
  ranked.sort((a, b) => a[0] - b[0] || a[1].name.localeCompare(b[1].name));
  return ranked.map(([, item]) => item);
}

function Tile({ item }: { item: DirectoryItem }) {
  return (
    <Link
      href={item.href}
      className="group flex gap-3 rounded-xl border border-fd-border bg-fd-card/50 p-3.5 transition-colors hover:border-fd-primary/40 hover:bg-fd-accent/40"
    >
      {item.icon ?? <AppMonogram name={item.name} size="sm" />}
      <span className="min-w-0">
        <span className="block truncate text-sm font-medium text-fd-foreground">{item.name}</span>
        <span className="mt-0.5 line-clamp-2 text-[13px] leading-snug text-fd-muted-foreground">
          {item.description}
        </span>
        <span className="mt-1.5 block text-xs text-fd-muted-foreground/80">{countLabel(item)}</span>
      </span>
    </Link>
  );
}

function TileGrid({ items }: { items: DirectoryItem[] }) {
  return (
    <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
      {items.map((item) => (
        <Tile key={item.id} item={item} />
      ))}
    </div>
  );
}

function SectionHeading({ id, title, children }: { id?: string; title: string; children?: ReactNode }) {
  return (
    <div className="mb-4 mt-12 first:mt-0">
      <h2 id={id} className="scroll-mt-28 text-lg font-semibold tracking-tight text-fd-foreground">
        {title}
      </h2>
      {children && <p className="mt-1 text-sm text-fd-muted-foreground">{children}</p>}
    </div>
  );
}

function letterOf(name: string): string {
  const first = normalize(name).match(/[a-z0-9]/)?.[0] ?? '#';
  return /[a-z]/.test(first) ? first.toUpperCase() : '#';
}

/** Every app by name, grouped by letter: the long tail, kept compact. */
function AppIndex({ items }: { items: DirectoryItem[] }) {
  const groups = useMemo(() => {
    const byLetter = new Map<string, DirectoryItem[]>();
    for (const item of items) {
      const letter = letterOf(item.name);
      byLetter.set(letter, [...(byLetter.get(letter) ?? []), item]);
    }
    return [...byLetter.entries()].sort(([a], [b]) =>
      a === '#' ? 1 : b === '#' ? -1 : a.localeCompare(b),
    );
  }, [items]);

  return (
    <>
      <nav aria-label="Apps by letter" className="mb-6 flex flex-wrap gap-1">
        {groups.map(([letter]) => (
          <a
            key={letter}
            href={`#apps-${letter === '#' ? 'other' : letter.toLowerCase()}`}
            className="inline-flex size-8 items-center justify-center rounded-lg text-sm font-medium text-fd-muted-foreground transition-colors hover:bg-fd-accent hover:text-fd-foreground"
          >
            {letter}
          </a>
        ))}
      </nav>
      <div className="columns-1 gap-8 sm:columns-2 lg:columns-3 xl:columns-4">
        {groups.map(([letter, group]) => (
          <section key={letter} className="mb-6 break-inside-avoid">
            <h3
              id={`apps-${letter === '#' ? 'other' : letter.toLowerCase()}`}
              className="mb-1.5 scroll-mt-28 text-xs font-semibold uppercase tracking-[0.08em] text-fd-primary"
            >
              {letter}
            </h3>
            <ul className="space-y-0.5">
              {group.map((item) => (
                <li key={item.id}>
                  <Link
                    href={item.href}
                    title={item.description}
                    className="flex items-baseline justify-between gap-3 rounded-md px-2 py-1 -mx-2 text-sm text-fd-foreground/90 transition-colors hover:bg-fd-accent/60 hover:text-fd-foreground"
                  >
                    <span className="truncate">{item.name}</span>
                    <span className="shrink-0 text-xs tabular-nums text-fd-muted-foreground/70">
                      {item.actions}
                    </span>
                  </Link>
                </li>
              ))}
            </ul>
          </section>
        ))}
      </div>
    </>
  );
}

function MissingApp() {
  return (
    <aside className="mt-14 rounded-2xl border border-fd-border bg-fd-card/60 p-5 text-sm leading-relaxed text-fd-muted-foreground">
      <p className="font-medium text-fd-foreground">Don&apos;t see the app you need?</p>
      <p className="mt-1">
        A workflow can still reach any service with a REST or GraphQL API through a{' '}
        <Link href="/docs/integrations/built-in/http" className="font-medium text-fd-primary hover:underline">
          Call an API
        </Link>{' '}
        step. Keep its key as a{' '}
        <Link href="/docs/concepts/connections#secrets" className="font-medium text-fd-primary hover:underline">
          workspace secret
        </Link>{' '}
        so it never sits in the workflow.
      </p>
    </aside>
  );
}

export function DirectoryBrowser({ items, popular, apps }: DirectoryBrowserProps) {
  const [query, setQuery] = useState('');
  const deferredQuery = useDeferredValue(query);
  const results = useMemo(
    () => (deferredQuery.trim() ? search(items, deferredQuery) : null),
    [items, deferredQuery],
  );

  const builtInItems = useMemo(() => items.filter((item) => item.builtIn), [items]);
  const appItems = useMemo(() => items.filter((item) => !item.builtIn), [items]);
  const popularItems = useMemo(() => {
    const byId = new Map(items.map((item) => [item.id, item]));
    return popular.flatMap((id) => byId.get(id) ?? []);
  }, [items, popular]);

  return (
    <div className="not-prose">
      <div role="search" className="relative">
        <Search
          aria-hidden="true"
          className="pointer-events-none absolute left-4 top-1/2 size-[18px] -translate-y-1/2 text-fd-muted-foreground"
        />
        <label htmlFor="integration-search" className="sr-only">
          Search integrations
        </label>
        <input
          id="integration-search"
          type="search"
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          placeholder={`Search ${apps} apps and built-in steps`}
          autoComplete="off"
          spellCheck={false}
          className="h-12 w-full rounded-xl border border-fd-border bg-fd-background pl-11 pr-11 text-[15px] text-fd-foreground shadow-sm outline-none transition-shadow placeholder:text-fd-muted-foreground focus:border-fd-primary/50 focus:ring-4 focus:ring-fd-primary/10 [&::-webkit-search-cancel-button]:hidden"
        />
        {query && (
          <button
            type="button"
            onClick={() => setQuery('')}
            aria-label="Clear search"
            className="absolute right-3 top-1/2 flex size-7 -translate-y-1/2 items-center justify-center rounded-md text-fd-muted-foreground hover:bg-fd-accent hover:text-fd-foreground"
          >
            <X className="size-4" />
          </button>
        )}
      </div>

      <p aria-live="polite" className="mt-3 text-sm text-fd-muted-foreground">
        {results
          ? results.length === 0
            ? `Nothing matches “${deferredQuery.trim()}”.`
            : `${results.length} ${results.length === 1 ? 'match' : 'matches'}`
          : null}
      </p>

      {results ? (
        <div className="mt-4">
          {results.length > 0 ? (
            <TileGrid items={results} />
          ) : (
            <MissingApp />
          )}
        </div>
      ) : (
        <div className="mt-6">
          <SectionHeading id="built-in-steps" title="Built-in steps">
            Lodol&apos;s own steps for decisions, loops, approvals, AI and working with data.
          </SectionHeading>
          <TileGrid items={builtInItems} />

          <SectionHeading id="popular-apps" title="Popular apps" />
          <TileGrid items={popularItems} />

          <SectionHeading id="all-apps" title={`All ${apps} apps`}>
            The number beside each app is how many actions it offers.
          </SectionHeading>
          <AppIndex items={appItems} />

          <MissingApp />
        </div>
      )}
    </div>
  );
}
