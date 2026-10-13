import { render, screen } from '@testing-library/react';
import { Endpoint, Example, Field, Fields } from '@/components/reference';
import { initialsFor } from '@/components/app-monogram';

describe('Fields', () => {
  it('lists its fields under a title', () => {
    render(
      <Fields title="Inputs">
        <Field name="Message ID" id="message_id" type="text" required description="Gmail message ID" />
      </Fields>,
    );
    expect(screen.getByRole('heading', { name: 'Inputs' })).toBeInTheDocument();
    expect(screen.getByText('Message ID')).toBeInTheDocument();
    expect(screen.getByText('message_id')).toBeInTheDocument();
    expect(screen.getByText('Required')).toBeInTheDocument();
    expect(screen.getByText('Gmail message ID')).toBeInTheDocument();
  });

  it('says there are none when it has no fields and nothing to say', () => {
    render(<Fields title="Inputs" />);
    expect(screen.getByText('None.')).toBeInTheDocument();
  });

  it('shows its description instead of "None" when it has one', () => {
    render(<Fields title="Outputs" description="This action has no output." />);
    expect(screen.getByText('This action has no output.')).toBeInTheDocument();
    expect(screen.queryByText('None.')).not.toBeInTheDocument();
  });
});

describe('Field', () => {
  it('shows an output by its key alone, with no Required badge', () => {
    render(
      <dl>
        <Field id="thread_id" type="text" description="Thread ID" />
      </dl>,
    );
    expect(screen.getByText('thread_id').tagName).toBe('CODE');
    expect(screen.queryByText('Required')).not.toBeInTheDocument();
  });

  it('shows values in its facts as code and the rest as text', () => {
    const { container } = render(
      <dl>
        <Field id="response" facts="One of: `approval` (Approve or reject), `reply`. Default: `approval`." />
      </dl>,
    );
    const codes = [...container.querySelectorAll('dd code')].map((c) => c.textContent);
    expect(codes).toEqual(['approval', 'reply', 'approval']);
    expect(container.querySelector('dd')).toHaveTextContent(
      'One of: approval (Approve or reject), reply. Default: approval.',
    );
  });

  it('keeps a value that holds a backtick whole', () => {
    const { container } = render(
      <dl>
        <Field id="x" facts="One of: ``x`y``." />
      </dl>,
    );
    expect(container.querySelector('dd code')).toHaveTextContent('x`y');
  });

  it('shows a description with markup characters exactly as written', () => {
    render(
      <dl>
        <Field id="text" description="Markdown works: **bold**, <b> and {braces}." />
      </dl>,
    );
    expect(screen.getByText('Markdown works: **bold**, <b> and {braces}.')).toBeInTheDocument();
  });
});

describe('Example', () => {
  it('starts closed, with a summary to open it', () => {
    const { container } = render(<Example>{'{}'}</Example>);
    expect(container.querySelector('details')).not.toHaveAttribute('open');
    expect(screen.getByText('Example output')).toBeInTheDocument();
  });
});

describe('Endpoint', () => {
  it('shows the method and the path', () => {
    render(<Endpoint method="POST" path="/api/v1/workflows/:id/run-async" />);
    expect(screen.getByText('POST')).toBeInTheDocument();
    expect(screen.getByText('/api/v1/workflows/:id/run-async')).toBeInTheDocument();
  });
});

describe('initialsFor', () => {
  it.each([
    ['Gmail', 'G'],
    ['Google Sheets', 'GS'],
    ['API-Football', 'AF'],
    ['Microsoft Dynamics 365', 'MD'],
    ['7shifts', '7'],
    ['(Unofficial) Bored API', 'UB'],
  ])('%s → %s', (name, initials) => {
    expect(initialsFor(name)).toBe(initials);
  });
});
