import { RootProvider } from 'fumadocs-ui/provider/next';
import { AskLodolWidget } from '@/components/ask-lodol/ask-lodol-widget';
import { appCountLabel, getCatalog } from '@/lib/catalog';
import '@fontsource-variable/onest';
import '@fontsource/new-amsterdam/latin-400.css';
import './global.css';
import type { ReactNode } from 'react';
import type { Metadata, Viewport } from 'next';

export function generateMetadata(): Metadata {
  return {
    metadataBase: new URL('https://docs.lodol.com'),
    title: {
      default: 'Lodol Docs',
      template: '%s · Lodol Docs',
    },
    // The count comes from the catalog, so it keeps up as apps are added.
    description: `Learn how to build, run and connect Lodol workflows: triggers, steps, approvals, AI agents, ${appCountLabel(getCatalog().apps)} app integrations and the developer API.`,
    openGraph: {
      siteName: 'Lodol Docs',
      type: 'website',
    },
  };
}

export const viewport: Viewport = {
  themeColor: [
    { media: '(prefers-color-scheme: light)', color: '#ffffff' },
    { media: '(prefers-color-scheme: dark)', color: '#0e0d12' },
  ],
};

export default function Layout({ children }: { children: ReactNode }) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className="flex flex-col min-h-screen" suppressHydrationWarning>
        <RootProvider>
          {children}
          <AskLodolWidget />
        </RootProvider>
      </body>
    </html>
  );
}
