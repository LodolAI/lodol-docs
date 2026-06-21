'use client';

import { useEffect, useRef, useState } from 'react';
import Link from 'next/link';
import {
  type ChatMessage,
  citationHref,
  formatCitationLabel,
  stripCitationMarkers,
} from '@/components/ask-lodol/citation';

// The docs site has a single deployment talking to one backend, so the prod
// build falls back to api-dev (no per-env build wiring needed). The env var is
// only an override for local dev (point at the proxy / a local server).
const API_BASE = (
  process.env.NEXT_PUBLIC_LODOL_API_BASE ?? 'https://api-dev.lodol.com'
).replace(/\/+$/, '');
// Client-side caps matching the server (chat_route.py DOCS_CHAT_* constants):
// query/message char limits mirror the server exactly; history is a tighter
// cap than the server's accepted max (50) since it keeps only the last 10 turns.
const MAX_QUERY_CHARS = 2000;
const MAX_HISTORY_ITEMS = 20;
const MAX_MESSAGE_CHARS = 4000;

function ChatIcon() {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>
    </svg>
  );
}

function SendIcon() {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M12 19V5"/>
      <path d="m5 12 7-7 7 7"/>
    </svg>
  );
}

function CloseIcon() {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M18 6 6 18"/>
      <path d="m6 6 12 12"/>
    </svg>
  );
}

export function AskLodolWidget() {
  const [open, setOpen] = useState(false);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState('');
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const listRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const triggerRef = useRef<HTMLButtonElement>(null);
  // Skip the focus effect on the initial (closed) mount so we don't steal
  // focus on page load; only act on actual open/close transitions.
  const interacted = useRef(false);

  useEffect(() => {
    if (open) {
      textareaRef.current?.focus();
    } else if (interacted.current) {
      // Return focus to the trigger when the dialog closes so keyboard and
      // screen-reader users aren't left on a detached element.
      triggerRef.current?.focus();
    }
    interacted.current = true;
  }, [open]);

  useEffect(() => {
    listRef.current?.scrollTo({ top: listRef.current.scrollHeight });
  }, [messages, pending]);

  // Grow the textarea with its content (capped), ChatGPT-style.
  useEffect(() => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = 'auto';
    el.style.height = `${Math.min(el.scrollHeight, 160)}px`;
  }, [input]);

  // Count code points (matches the server's Python len()), not UTF-16 units.
  const charCount = [...input].length;
  const overLimit = charCount > MAX_QUERY_CHARS;
  const canSend = !pending && !overLimit && input.trim().length > 0;

  async function send() {
    if (!canSend) return;
    const query = input.trim();
    const history = messages.slice(-MAX_HISTORY_ITEMS).map((m) =>
      m.role === 'assistant'
        ? {
            role: m.role,
            content: m.content.slice(0, MAX_MESSAGE_CHARS),
            has_enough_context: m.hasEnoughContext,
          }
        : { role: m.role, content: m.content.slice(0, MAX_MESSAGE_CHARS) },
    );
    setMessages((prev) => [...prev, { role: 'user', content: query }]);
    setInput('');
    setError(null);
    setPending(true);

    // On failure, drop the optimistic user turn so it doesn't linger as an
    // orphan in history, and restore the input so the question can be retried.
    const fail = (message: string) => {
      setMessages((prev) => prev.slice(0, -1));
      setInput(query);
      setError(message);
    };

    try {
      const res = await fetch(`${API_BASE}/docs/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query, history }),
      });
      if (res.status === 429) {
        const retryAfter = res.headers.get('Retry-After');
        fail(
          retryAfter
            ? `Too many questions — try again in ${retryAfter} seconds.`
            : 'Too many questions — please wait a moment and try again.',
        );
        return;
      }
      if (!res.ok) {
        let message = 'Something went wrong. Please try again.';
        try {
          const body = await res.json();
          if (typeof body.error === 'string') message = body.error;
        } catch {
          // keep the generic message
        }
        fail(message);
        return;
      }
      const data = await res.json();
      if (typeof data.answer !== 'string') {
        fail('Something went wrong. Please try again.');
        return;
      }
      const hasEnoughContext = data.has_enough_context === true;
      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          content: data.answer,
          hasEnoughContext,
          citation:
            hasEnoughContext && data.citations?.length > 0
              ? data.citations[0]
              : null,
        },
      ]);
    } catch {
      fail('Could not reach the Lodol API. Please try again.');
    } finally {
      setPending(false);
    }
  }

  return (
    <>
      {!open && (
        <button
          ref={triggerRef}
          type="button"
          onClick={() => setOpen(true)}
          aria-label="Ask Lodol"
          className="fixed bottom-4 right-4 z-50 flex size-12 items-center justify-center rounded-full bg-fd-primary text-fd-primary-foreground shadow-lg transition-transform hover:scale-105"
        >
          <ChatIcon />
        </button>
      )}
      {open && (
        <div
          role="dialog"
          aria-label="Ask Lodol"
          onKeyDown={(e) => {
            if (e.key === 'Escape') setOpen(false);
          }}
          className="fixed bottom-4 right-4 z-50 flex h-[min(28rem,calc(100dvh-2rem))] w-[min(24rem,calc(100vw-2rem))] flex-col overflow-hidden rounded-xl border border-fd-border bg-fd-popover text-fd-popover-foreground shadow-lg"
        >
          <div className="flex items-center justify-between border-b border-fd-border px-4 py-3">
            <span className="text-sm font-medium">Ask Lodol</span>
            <button
              type="button"
              onClick={() => setOpen(false)}
              aria-label="Close"
              className="rounded-md p-1 text-fd-muted-foreground hover:bg-fd-accent hover:text-fd-accent-foreground"
            >
              <CloseIcon />
            </button>
          </div>
          <div ref={listRef} className="flex flex-1 flex-col gap-3 overflow-y-auto px-4 py-3">
            {messages.map((message, i) =>
              message.role === 'user' ? (
                <div
                  key={i}
                  className="ml-8 max-w-full self-end whitespace-pre-wrap break-words rounded-lg bg-fd-primary/10 px-3 py-2 text-sm"
                >
                  {message.content}
                </div>
              ) : (
                <div key={i} className="mr-8 self-start">
                  <div className="whitespace-pre-wrap break-words rounded-lg bg-fd-muted px-3 py-2 text-sm">
                    {stripCitationMarkers(message.content)}
                  </div>
                  {message.citation && (
                    <p className="mt-1 px-1 text-xs text-fd-muted-foreground">
                      Source:{' '}
                      <Link
                        href={citationHref(message.citation)}
                        className="underline hover:text-fd-accent-foreground"
                      >
                        {formatCitationLabel(message.citation)}
                      </Link>
                    </p>
                  )}
                </div>
              ),
            )}
            {pending && (
              <div className="mr-8 self-start rounded-lg bg-fd-muted px-3 py-2 text-sm text-fd-muted-foreground">
                Thinking…
              </div>
            )}
          </div>
          <div className="border-t border-fd-border px-4 py-3">
            {error && <p className="mb-2 text-xs text-red-500">{error}</p>}
            <div className="relative rounded-lg border border-fd-border bg-fd-muted/40 px-3 py-2.5 focus-within:ring-1 focus-within:ring-fd-primary">
              <textarea
                ref={textareaRef}
                rows={1}
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    void send();
                  }
                }}
                placeholder="Ask a question…"
                className="block max-h-40 w-full resize-none bg-transparent pr-10 text-sm leading-6 focus:outline-none"
              />
              <button
                type="button"
                onClick={() => void send()}
                disabled={!canSend}
                aria-label="Send"
                className="absolute right-2 top-1/2 flex size-8 -translate-y-1/2 items-center justify-center rounded-md bg-fd-primary text-fd-primary-foreground transition-opacity disabled:opacity-40"
              >
                <SendIcon />
              </button>
            </div>
            <p className={`mt-1 text-xs ${overLimit ? 'text-red-500' : 'text-fd-muted-foreground'}`}>
              {charCount}/{MAX_QUERY_CHARS} characters
            </p>
          </div>
        </div>
      )}
    </>
  );
}
