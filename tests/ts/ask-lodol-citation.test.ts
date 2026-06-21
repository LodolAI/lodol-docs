import {
  type Citation,
  citationHref,
  formatCitationLabel,
  stripCitationMarkers,
} from '@/components/ask-lodol/citation';

function makeCitation(overrides: Partial<Citation>): Citation {
  return {
    index: 1,
    chunk_id: 'abc123',
    page_title: 'Authentication',
    heading_anchor: null,
    url: 'https://docs.lodol.com/docs/guides/authentication',
    ...overrides,
  };
}

describe('formatCitationLabel', () => {
  it('shows "title > heading" with the heading de-slugified', () => {
    const citation = makeCitation({
      page_title: 'Workflows API',
      heading_anchor: 'create-a-workflow',
    });
    expect(formatCitationLabel(citation)).toBe('Workflows API > Create a workflow');
  });

  it('shows only the page title when there is no heading anchor', () => {
    const citation = makeCitation({ heading_anchor: null });
    expect(formatCitationLabel(citation)).toBe('Authentication');
  });

  it('shows only the page title when the heading duplicates it', () => {
    const citation = makeCitation({
      page_title: 'Authentication',
      heading_anchor: 'authentication',
    });
    expect(formatCitationLabel(citation)).toBe('Authentication');
  });

  it('dedupes multi-word titles against their slugified anchor', () => {
    const citation = makeCitation({
      page_title: 'Error Handling',
      heading_anchor: 'error-handling',
    });
    expect(formatCitationLabel(citation)).toBe('Error Handling');
  });
});

describe('citationHref', () => {
  it('converts an absolute docs URL to a site-relative path with anchor', () => {
    const citation = makeCitation({
      url: 'https://docs.lodol.com/docs/guides/quickstart#step-1-create-an-api-key',
    });
    expect(citationHref(citation)).toBe('/docs/guides/quickstart#step-1-create-an-api-key');
  });

  it('converts an anchor-less URL to a plain relative path', () => {
    const citation = makeCitation({
      url: 'https://docs.lodol.com/docs/guides/authentication',
    });
    expect(citationHref(citation)).toBe('/docs/guides/authentication');
  });

  it('passes a malformed URL through unchanged', () => {
    const citation = makeCitation({ url: 'not a url' });
    expect(citationHref(citation)).toBe('not a url');
  });
});

describe('stripCitationMarkers', () => {
  it('removes inline [n] markers and the space before them', () => {
    expect(stripCitationMarkers('Use the API [1] and retry [2].')).toBe(
      'Use the API and retry.',
    );
  });

  it('leaves text without markers unchanged', () => {
    expect(stripCitationMarkers('No citations here.')).toBe('No citations here.');
  });

  it('preserves array indices in code (alphanumeric before the bracket)', () => {
    expect(stripCitationMarkers('Read response.choices[0].message [1].')).toBe(
      'Read response.choices[0].message.',
    );
  });

  it('removes runs of adjacent markers together', () => {
    expect(stripCitationMarkers('See the guide [1][2] for details.')).toBe(
      'See the guide for details.',
    );
  });
});
