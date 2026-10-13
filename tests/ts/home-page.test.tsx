import { render, screen, within } from '@testing-library/react';
import HomePage from '@/app/(home)/page';
import type { Catalog } from '@/lib/catalog';

jest.mock('next/link', () => {
  const MockLink = ({
    href,
    children,
    ...rest
  }: {
    href: string;
    children: React.ReactNode;
  }) => (
    <a href={href} {...rest}>
      {children}
    </a>
  );
  MockLink.displayName = 'MockLink';
  return { __esModule: true, default: MockLink };
});

jest.mock('@/components/home-search', () => ({
  HomeSearch: () => <button type="button">Search the docs</button>,
}));

jest.mock('@/components/integration-icon', () => ({
  IntegrationIcon: () => null,
}));

const catalog: Catalog = {
  apps: 832,
  appActions: 9917,
  popular: ['gmail', 'not_in_catalog', 'slack'],
  groups: [],
  entries: [
    { id: 'skipflow_review', name: 'Approvals', description: 'Pause for a person.', href: '/docs/integrations/built-in/review', actions: 1, builtIn: true, icon: 'UserCheck' },
    { id: 'skipflow_conditions', name: 'Decisions', description: 'Choose which steps run.', href: '/docs/integrations/built-in/conditions', actions: 2, builtIn: true, icon: 'Split' },
    { id: 'skipflow_random', name: 'Random', description: 'Pick random numbers.', href: '/docs/integrations/built-in/random', actions: 4, builtIn: true, icon: 'Dices' },
    { id: 'gmail', name: 'Gmail', description: 'Send email.', href: '/docs/integrations/gmail', actions: 14, builtIn: false },
    { id: 'slack', name: 'Slack', description: 'Send messages.', href: '/docs/integrations/slack', actions: 79, builtIn: false },
  ],
};

jest.mock('@/lib/catalog', () => ({
  getCatalog: () => catalog,
}));

describe('HomePage', () => {
  it('leads with what Lodol does', () => {
    render(<HomePage />);
    const heading = screen.getByRole('heading', { level: 1 });
    expect(heading).toHaveTextContent('Build it once.');
    expect(heading).toHaveTextContent('Lodol runs it every time.');
  });

  it('offers a search of the docs', () => {
    render(<HomePage />);
    expect(screen.getByRole('button', { name: 'Search the docs' })).toBeInTheDocument();
  });

  it.each([
    ['Build with your AI tool', '/docs/build-with-ai'],
    ['Learn how workflows work', '/docs/concepts/workflows'],
    ['Run workflows from your code', '/docs/api/quickstart'],
  ])('starts "%s" at %s', (title, href) => {
    render(<HomePage />);
    const link = screen.getByRole('link', { name: new RegExp(title) });
    expect(link).toHaveAttribute('href', href);
  });

  it('features a few built-in steps in a set order, and leaves the rest to the directory', () => {
    render(<HomePage />);
    const decisions = screen.getByRole('link', { name: 'Decisions' });
    const approvals = screen.getByRole('link', { name: 'Approvals' });
    expect(decisions).toHaveAttribute('href', '/docs/integrations/built-in/conditions');
    expect(approvals).toHaveAttribute('href', '/docs/integrations/built-in/review');
    expect(decisions.compareDocumentPosition(approvals) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
    expect(screen.queryByRole('link', { name: 'Random' })).not.toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'All built-in steps' })).toHaveAttribute(
      'href',
      '/docs/integrations#built-in-steps',
    );
  });

  it('counts apps and actions from the catalog rather than a fixed number', () => {
    render(<HomePage />);
    expect(
      screen.getByRole('heading', { name: '832 apps, 9,917 actions' }),
    ).toBeInTheDocument();
  });

  it('shows the popular apps in order, skipping any the catalog lacks', () => {
    render(<HomePage />);
    const section = screen.getByRole('heading', { name: /apps, .* actions/ }).closest('section')!;
    const names = within(section)
      .getAllByRole('listitem')
      .map((item) => item.textContent);
    expect(names).toEqual(['Gmail', 'Slack']);
  });

  it('links to the integrations directory', () => {
    render(<HomePage />);
    expect(screen.getByRole('link', { name: /Browse integrations/ })).toHaveAttribute(
      'href',
      '/docs/integrations',
    );
  });

  it('opens outside resources in a new tab', () => {
    render(<HomePage />);
    const status = screen.getByRole('link', { name: /Service status/ });
    expect(status).toHaveAttribute('href', 'https://status.lodol.com');
    expect(status).toHaveAttribute('target', '_blank');
    expect(status).toHaveAttribute('rel', 'noopener noreferrer');
  });
});
