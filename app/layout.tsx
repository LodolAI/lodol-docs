import { RootProvider } from 'fumadocs-ui/provider/next';
import { AskLodolWidget } from '@/components/ask-lodol/ask-lodol-widget';
import '@fontsource-variable/onest';
import '@fontsource/new-amsterdam/latin-400.css';
import './global.css';
import type { ReactNode } from 'react';
import type { Metadata, Viewport } from 'next';

export const metadata: Metadata = {
  metadataBase: new URL('https://docs.lodol.com'),
  title: {
    default: 'Lodol Docs',
    template: '%s · Lodol Docs',
  },
  description:
    'Learn how to build, run and connect Lodol workflows: triggers, steps, approvals, AI agents, 800+ app integrations and the developer API.',
  openGraph: {
    siteName: 'Lodol Docs',
    type: 'website',
  },
};

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
