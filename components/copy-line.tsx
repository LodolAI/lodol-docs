'use client';

import { useEffect, useRef, useState } from 'react';
import { Check, Copy } from 'lucide-react';

/**
 * One line to copy, such as a command or a URL: the text in mono, and a
 * button that copies it and says so for a moment.
 */
export function CopyLine({ label, value }: { label: string; value: string }) {
  const [copied, setCopied] = useState(false);
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => () => {
    if (timer.current) clearTimeout(timer.current);
  }, []);

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(value);
    } catch {
      return;
    }
    setCopied(true);
    if (timer.current) clearTimeout(timer.current);
    timer.current = setTimeout(() => setCopied(false), 1600);
  };

  return (
    <div>
      <p className="mb-1.5 text-xs font-medium text-fd-muted-foreground">{label}</p>
      <div className="flex items-center gap-2 rounded-lg border border-fd-border bg-fd-muted px-3 py-2">
        <code className="min-w-0 flex-1 overflow-x-auto whitespace-nowrap font-mono text-[12.5px] text-fd-foreground [scrollbar-width:none]">
          {value}
        </code>
        <button
          type="button"
          onClick={copy}
          aria-label={copied ? `${label} copied` : `Copy ${label.toLowerCase()}`}
          className="inline-flex size-7 shrink-0 items-center justify-center rounded-md text-fd-muted-foreground transition-colors hover:bg-fd-accent hover:text-fd-foreground"
        >
          {copied ? <Check aria-hidden="true" className="size-4 text-emerald-600" /> : <Copy aria-hidden="true" className="size-4" />}
        </button>
      </div>
    </div>
  );
}
