import { RootProvider } from 'fumadocs-ui/provider/next';
import { AskLodolWidget } from '@/components/ask-lodol/ask-lodol-widget';
import './global.css';
import type { ReactNode } from 'react';
import type { Metadata } from 'next';

export const metadata: Metadata = {
  title: {
    default: 'Lodol Developer API',
    template: '%s | Lodol Docs',
  },
  description: 'Developer documentation for the Lodol API',
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
