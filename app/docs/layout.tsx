import { source } from '@/lib/source';
import { DocsLayout } from 'fumadocs-ui/layouts/docs';
import { baseOptions } from '@/lib/layout.shared';
import { ThemeSwitch } from 'fumadocs-ui/layouts/shared/slots/theme-switch';
import type { ReactNode } from 'react';

function GlobeIcon() {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <circle cx="12" cy="12" r="10"/>
      <path d="M2 12h20"/>
      <path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"/>
    </svg>
  );
}

function GitHubIcon() {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
      <path d="M12 0C5.374 0 0 5.373 0 12c0 5.302 3.438 9.8 8.207 11.387.599.111.793-.261.793-.577v-2.234c-3.338.726-4.033-1.416-4.033-1.416-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-.729 1.205.084 1.839 1.237 1.839 1.237 1.07 1.834 2.807 1.304 3.492.997.107-.775.418-1.305.762-1.604-2.665-.305-5.467-1.334-5.467-5.931 0-1.311.469-2.381 1.236-3.221-.124-.303-.535-1.524.117-3.176 0 0 1.008-.322 3.301 1.23A11.509 11.509 0 0 1 12 5.803c1.02.005 2.047.138 3.006.404 2.291-1.552 3.297-1.23 3.297-1.23.653 1.653.242 2.874.118 3.176.77.84 1.235 1.911 1.235 3.221 0 4.609-2.807 5.624-5.479 5.921.43.372.823 1.102.823 2.222v3.293c0 .319.192.694.801.576C20.566 21.797 24 17.3 24 12c0-6.627-5.373-12-12-12z"/>
    </svg>
  );
}

function SidebarFooterLinks() {
  return (
    <div className="flex flex-col gap-1 px-2 py-2 border-t border-fd-border">
      <a
        href="https://www.lodol.com/"
        target="_blank"
        rel="noopener noreferrer"
        className="flex items-center gap-2 rounded-md px-2 py-1.5 text-sm text-fd-muted-foreground hover:bg-fd-accent hover:text-fd-accent-foreground transition-colors"
      >
        <GlobeIcon />
        Go to website
      </a>
      <a
        href="https://github.com/LodolAI/lodol-docs"
        target="_blank"
        rel="noopener noreferrer"
        className="flex items-center gap-2 rounded-md px-2 py-1.5 text-sm text-fd-muted-foreground hover:bg-fd-accent hover:text-fd-accent-foreground transition-colors"
      >
        <GitHubIcon />
        Go to GitHub
      </a>
      <div className="pt-1">
        <ThemeSwitch />
      </div>
    </div>
  );
}

export default function Layout({ children }: { children: ReactNode }) {
  return (
    <DocsLayout
      tree={source.pageTree}
      {...baseOptions()}
      themeSwitch={{ enabled: false }}
      sidebar={{ footer: <SidebarFooterLinks /> }}
    >
      {children}
    </DocsLayout>
  );
}
