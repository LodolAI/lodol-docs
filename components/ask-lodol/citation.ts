/**
 * Types and pure helpers for rendering Ask Lodol answers and citations.
 *
 * The shapes mirror the server's POST /docs/chat contract
 * (skipflow/api/routes/docs/chat_route.py in the lodol server repo).
 */

export interface Citation {
  /** 1-based number matching the [n] markers in the answer text. */
  index: number;
  chunk_id: string;
  page_title: string;
  /** Slug of the cited section heading, or null for whole-page chunks. */
  heading_anchor: string | null;
  /** Absolute URL to the cited section, including #anchor when present. */
  url: string;
}

export type ChatMessage =
  | { role: 'user'; content: string }
  | {
      role: 'assistant';
      content: string;
      citation: Citation | null;
      /** Echoed back in history so the server can drop dead "no answer" turns. */
      hasEnoughContext: boolean;
    };

function slugify(text: string): string {
  return text
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '');
}

function deslugify(slug: string): string {
  const words = slug.replace(/-/g, ' ');
  return words.charAt(0).toUpperCase() + words.slice(1);
}

/**
 * "Workflows API > Create a workflow", or just the page title when the
 * citation has no section heading or the heading repeats the page title.
 * The anchor is a slug, so the heading is de-slugified for display; if the
 * backend ever returns the original heading text, only this function changes.
 */
export function formatCitationLabel(citation: Citation): string {
  if (
    !citation.heading_anchor ||
    slugify(citation.page_title) === citation.heading_anchor
  ) {
    return citation.page_title;
  }
  return `${citation.page_title} > ${deslugify(citation.heading_anchor)}`;
}

/**
 * Convert the citation's absolute docs URL into a site-relative href so
 * links navigate correctly on localhost and preview deploys too.
 */
export function citationHref(citation: Citation): string {
  try {
    const url = new URL(citation.url);
    return url.pathname + url.search + url.hash;
  } catch {
    return citation.url;
  }
}

/**
 * Remove inline [n] citation markers from the answer text. The UI shows a
 * single source line instead, so the markers would point at nothing.
 *
 * Only brackets that follow whitespace (or the start of the text) are treated
 * as markers; an alphanumeric before the bracket means array indexing in a
 * code sample (e.g. `choices[0]`), which must be preserved. Runs of adjacent
 * markers ("[1][2]") are stripped together.
 */
export function stripCitationMarkers(answer: string): string {
  return answer.replace(/(?:^|\s)\[\d+\](?:\[\d+\])*/g, '');
}
