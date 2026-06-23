import { createSseDecoder } from '@/components/ask-lodol/stream';

function token(text: string): string {
  return `event: token\ndata: ${JSON.stringify({ text })}\n\n`;
}

describe('createSseDecoder', () => {
  it('decodes token and done events from a single chunk', () => {
    const decoder = createSseDecoder();
    const done =
      'event: done\ndata: {"has_enough_context": true, "citations": [' +
      '{"index": 1, "chunk_id": "c1", "page_title": "Quickstart",' +
      ' "heading_anchor": "install",' +
      ' "url": "https://docs.lodol.com/docs/quickstart#install"}]}\n\n';

    const events = decoder.push(token('Hello ') + token('world') + done);

    expect(events).toEqual([
      { type: 'token', text: 'Hello ' },
      { type: 'token', text: 'world' },
      {
        type: 'done',
        hasEnoughContext: true,
        citation: {
          index: 1,
          chunk_id: 'c1',
          page_title: 'Quickstart',
          heading_anchor: 'install',
          url: 'https://docs.lodol.com/docs/quickstart#install',
        },
      },
    ]);
  });

  it('buffers an event split across chunks', () => {
    const decoder = createSseDecoder();
    expect(decoder.push('event: token\ndata: {"text": "par')).toEqual([]);
    expect(decoder.push('tial"}\n\n')).toEqual([{ type: 'token', text: 'partial' }]);
  });

  it('handles a single event split exactly on the blank-line separator', () => {
    const decoder = createSseDecoder();
    expect(decoder.push(`event: token\ndata: {"text": "x"}\n`)).toEqual([]);
    expect(decoder.push('\n')).toEqual([{ type: 'token', text: 'x' }]);
  });

  it('normalizes CRLF line endings', () => {
    const decoder = createSseDecoder();
    const events = decoder.push('event: token\r\ndata: {"text": "ok"}\r\n\r\n');
    expect(events).toEqual([{ type: 'token', text: 'ok' }]);
  });

  it('decodes an error event', () => {
    const decoder = createSseDecoder();
    expect(
      decoder.push('event: error\ndata: {"error": "boom"}\n\n'),
    ).toEqual([{ type: 'error', error: 'boom' }]);
  });

  it('reports no citation when has_enough_context is false', () => {
    const decoder = createSseDecoder();
    const events = decoder.push(
      'event: done\ndata: {"has_enough_context": false, "citations": []}\n\n',
    );
    expect(events).toEqual([
      { type: 'done', hasEnoughContext: false, citation: null },
    ]);
  });

  it('skips malformed JSON without throwing', () => {
    const decoder = createSseDecoder();
    const events = decoder.push(
      'event: token\ndata: {not json}\n\n' + token('after'),
    );
    expect(events).toEqual([{ type: 'token', text: 'after' }]);
  });
});
