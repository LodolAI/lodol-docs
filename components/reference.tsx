import { Children, type ReactNode } from 'react';
import { ChevronRight } from 'lucide-react';

// The building blocks of the generated integration reference and the API
// pages: a list of fields (an action's inputs or outputs, an endpoint's
// parameters), and an example tucked away until it's wanted.

/** Text with `code` spans, shown with the spans as code. */
function WithCode({ text }: { text: string }) {
  const parts: ReactNode[] = [];
  const span = /(`+)([\s\S]*?[^`])\1(?!`)/g;
  let last = 0;
  for (const match of text.matchAll(span)) {
    if (match.index > last) parts.push(text.slice(last, match.index));
    parts.push(<code key={match.index}>{match[2].trim() || match[2]}</code>);
    last = match.index + match[0].length;
  }
  if (last < text.length) parts.push(text.slice(last));
  return <>{parts}</>;
}

interface FieldsProps {
  title: string;
  /** A sentence about the list as a whole, such as what an action returns. */
  description?: string;
  children?: ReactNode;
}

export function Fields({ title, description, children }: FieldsProps) {
  const empty = Children.count(children) === 0;
  return (
    <section aria-label={title} className="not-prose lf">
      <h3 className="lf-title">{title}</h3>
      {description && <p className="lf-note">{description}</p>}
      {!empty && (
        <dl className="lf-list">{children}</dl>
      )}
      {empty && !description && <p className="lf-note">None.</p>}
    </section>
  );
}

interface FieldProps {
  /** The label the editor shows. Outputs have none: their key is their name. */
  name?: string;
  /** The key a workflow's JSON and the API use. */
  id: string;
  type?: string;
  required?: boolean;
  description?: string;
  /** Choices, range and default, with values written as `code`. */
  facts?: string;
}

export function Field({ name, id, type, required, description, facts }: FieldProps) {
  // Styled by the lf-* classes in app/global.css.
  return (
    <div className="lf-row">
      <dt className="lf-head">
        {name ? (
          <>
            <span className="lf-name">{name}</span>
            <code className="lf-key">{id}</code>
          </>
        ) : (
          <code className="lf-key-only">{id}</code>
        )}
        {type && <span className="lf-type">{type}</span>}
        {required && <span className="lf-req">Required</span>}
      </dt>
      {(description || facts) && (
        <dd className="lf-desc">
          {description}
          {facts && (
            <span className={description ? 'lf-facts' : undefined}>
              <WithCode text={facts} />
            </span>
          )}
        </dd>
      )}
    </div>
  );
}

/** An example, closed until the reader opens it. */
export function Example({
  title = 'Example output',
  children,
}: {
  title?: string;
  children: ReactNode;
}) {
  return (
    <details className="lf-example">
      <summary>
        <ChevronRight aria-hidden="true" />
        {title}
      </summary>
      <div>{children}</div>
    </details>
  );
}

const METHOD_STYLES: Record<string, string> = {
  GET: 'bg-emerald-500/12 text-emerald-700 dark:text-emerald-300',
  POST: 'bg-brand-soft text-brand-strong dark:bg-brand/20 dark:text-brand-lilac',
  DELETE: 'bg-red-500/12 text-red-700 dark:text-red-300',
};

/** An API endpoint: its method and path. */
export function Endpoint({ method, path }: { method: string; path: string }) {
  return (
    <div className="not-prose my-5 flex items-center gap-3 overflow-x-auto rounded-xl border border-fd-border bg-fd-card px-4 py-3 font-mono text-sm">
      <span
        className={`rounded-md px-2 py-0.5 text-xs font-semibold tracking-wide ${METHOD_STYLES[method] ?? 'bg-fd-muted'}`}
      >
        {method}
      </span>
      <span className="whitespace-nowrap text-fd-foreground">{path}</span>
    </div>
  );
}
