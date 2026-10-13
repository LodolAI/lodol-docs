'use client';

import { Search } from 'lucide-react';
import { useSearchContext } from 'fumadocs-ui/contexts/search';

/** A search field that opens the docs search, for the home page. */
export function HomeSearch() {
  const { setOpenSearch } = useSearchContext();
  return (
    <button
      type="button"
      onClick={() => setOpenSearch(true)}
      className="flex h-12 w-full max-w-md items-center gap-3 rounded-xl border border-fd-border bg-fd-background/80 px-4 text-left text-[15px] text-fd-muted-foreground shadow-sm backdrop-blur transition-colors hover:border-fd-primary/40 hover:text-fd-foreground"
    >
      <Search aria-hidden="true" className="size-[18px]" />
      Search the docs
    </button>
  );
}
