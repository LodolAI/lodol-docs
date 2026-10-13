import { IntegrationIcon } from '@/components/integration-icon';
import { cn } from '@/lib/cn';

interface PreviewStep {
  /** The step's name, as the editor shows it: "Append row". */
  step: string;
  /** The app it belongs to; leave out for a built-in step. */
  app?: string;
  /** A built-in step's icon (a lucide name), e.g. "Split" for If. */
  icon?: string;
  /** Marks the step that starts the workflow. */
  trigger?: boolean;
  /** How many sections (If, Repeat) the step sits inside. */
  depth?: number;
  /** A short note on what the step reads or does: "@payment.amount". */
  note?: string;
}

/**
 * A workflow drawn the way the editor lists it: a trigger, then steps, one
 * under the other. Steps inside an If or a Repeat are indented.
 */
export function WorkflowPreview({
  title,
  steps,
  caption,
}: {
  title?: string;
  steps: PreviewStep[];
  caption?: string;
}) {
  return (
    <figure className="not-prose my-8">
      <div className="rounded-2xl border border-fd-border bg-[radial-gradient(circle_at_1px_1px,color-mix(in_oklab,var(--color-fd-foreground)_9%,transparent)_1px,transparent_0)] bg-[size:16px_16px] p-4 sm:p-6">
        {title && (
          <p className="mb-4 text-xs font-semibold uppercase tracking-[0.08em] text-fd-muted-foreground">
            {title}
          </p>
        )}
        <ol className="space-y-0">
          {steps.map((step, i) => (
            <li key={i} style={{ paddingLeft: `${(step.depth ?? 0) * 1.75}rem` }}>
              {i > 0 && (
                <div aria-hidden="true" className="ml-[1.375rem] h-4 w-px bg-fd-border" />
              )}
              <div
                className={cn(
                  'flex items-center gap-3 rounded-xl border bg-fd-background px-3 py-2.5 shadow-[0_1px_2px_rgba(0,0,0,0.04)]',
                  step.trigger ? 'border-fd-primary/40' : 'border-fd-border',
                )}
              >
                <IntegrationIcon
                  name={step.app ?? step.step}
                  icon={step.icon}
                  builtIn={!step.app}
                  size="sm"
                />
                <div className="min-w-0 flex-1">
                  <p className="truncate text-sm font-medium text-fd-foreground">{step.step}</p>
                  <p className="truncate text-xs text-fd-muted-foreground">
                    {step.app ?? 'Built-in step'}
                    {step.note && (
                      <>
                        {' · '}
                        <span className={step.note.includes('@') ? 'font-mono' : undefined}>
                          {step.note}
                        </span>
                      </>
                    )}
                  </p>
                </div>
                {step.trigger && (
                  <span className="shrink-0 rounded-full bg-brand-soft px-2 py-0.5 text-[11px] font-medium text-brand-strong dark:bg-brand/20 dark:text-brand-lilac">
                    Trigger
                  </span>
                )}
              </div>
            </li>
          ))}
        </ol>
      </div>
      {caption && (
        <figcaption className="mt-3 text-center text-sm text-fd-muted-foreground">{caption}</figcaption>
      )}
    </figure>
  );
}
