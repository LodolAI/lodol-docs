import { source } from '@/lib/source';
import { DocsLayout } from 'fumadocs-ui/layouts/notebook';
import { baseOptions } from '@/lib/layout.shared';
import type { ReactNode } from 'react';

// Documentation, Integrations and API are top-level tabs in the navbar, each
// with its own sidebar: the folders marked "root" in content/docs.
export default function Layout({ children }: { children: ReactNode }) {
  const base = baseOptions();
  return (
    <DocsLayout
      {...base}
      tree={source.pageTree}
      nav={{ ...base.nav, mode: 'top' }}
      tabMode="navbar"
    >
      {children}
    </DocsLayout>
  );
}
