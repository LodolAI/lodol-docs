/**
 * Incremental Server-Sent Events decoder for the Ask Lodol streaming endpoint
 * (POST /docs/chat/stream — see chat_stream_route.py in the lodol server repo).
 *
 * The widget reads the response body as a stream of bytes; chunk boundaries
 * don't align with SSE event boundaries, so {@link createSseDecoder} buffers
 * across chunks and emits whole events as they complete.
 */

import type { Citation } from '@/components/ask-lodol/citation';

export type StreamEvent =
  | { type: 'token'; text: string }
  | { type: 'done'; hasEnoughContext: boolean; citation: Citation | null }
  | { type: 'error'; error: string };

export interface SseDecoder {
  /** Feed a decoded text chunk; returns the events that completed in it. */
  push(chunk: string): StreamEvent[];
}

export function createSseDecoder(): SseDecoder {
  let buffer = '';
  return {
    push(chunk: string): StreamEvent[] {
      // Normalize CRLF so event/field splitting is separator-agnostic.
      buffer += chunk.replace(/\r\n/g, '\n');
      const events: StreamEvent[] = [];
      let sep = buffer.indexOf('\n\n');
      while (sep !== -1) {
        const block = buffer.slice(0, sep);
        buffer = buffer.slice(sep + 2);
        const event = parseBlock(block);
        if (event) events.push(event);
        sep = buffer.indexOf('\n\n');
      }
      return events;
    },
  };
}

function parseBlock(block: string): StreamEvent | null {
  let name = 'message';
  const dataLines: string[] = [];
  for (const line of block.split('\n')) {
    if (line.startsWith('event:')) {
      name = line.slice('event:'.length).trim();
    } else if (line.startsWith('data:')) {
      dataLines.push(line.slice('data:'.length).trim());
    }
  }
  if (dataLines.length === 0) return null;

  let data: Record<string, unknown>;
  try {
    data = JSON.parse(dataLines.join('\n'));
  } catch {
    return null;
  }

  if (name === 'token' && typeof data.text === 'string') {
    return { type: 'token', text: data.text };
  }
  if (name === 'done') {
    const citations = Array.isArray(data.citations)
      ? (data.citations as Citation[])
      : [];
    const hasEnoughContext = data.has_enough_context === true;
    return {
      type: 'done',
      hasEnoughContext,
      citation: hasEnoughContext && citations.length > 0 ? citations[0] : null,
    };
  }
  if (name === 'error') {
    return {
      type: 'error',
      error:
        typeof data.error === 'string'
          ? data.error
          : 'Something went wrong. Please try again.',
    };
  }
  return null;
}
