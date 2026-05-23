import { render, screen } from '@testing-library/react';
import HomePage from '@/app/(home)/page';

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

describe('HomePage', () => {
  it('renders the marketing heading', () => {
    render(<HomePage />);
    expect(
      screen.getByRole('heading', { name: /Lodol Developer API/i, level: 1 }),
    ).toBeInTheDocument();
  });

  it('shows the introductory copy describing the API', () => {
    render(<HomePage />);
    expect(
      screen.getByText(/Build powerful integrations with the Lodol API/i),
    ).toBeInTheDocument();
  });

  it('links "Get Started" to the docs root', () => {
    render(<HomePage />);
    const link = screen.getByRole('link', { name: /Get Started/i });
    expect(link).toHaveAttribute('href', '/docs');
  });

  it('links "API Reference" to the API reference page', () => {
    render(<HomePage />);
    const link = screen.getByRole('link', { name: /API Reference/i });
    expect(link).toHaveAttribute('href', '/docs/api-reference');
  });

  it('exposes feature card links alongside the primary CTAs', () => {
    render(<HomePage />);
    const links = screen.getAllByRole('link');
    expect(links.length).toBeGreaterThan(2);
  });

  it('links "Quickstart" to the quickstart guide', () => {
    render(<HomePage />);
    const link = screen.getByRole('link', { name: /Quickstart/i });
    expect(link).toHaveAttribute('href', '/docs/guides/quickstart');
  });

  it('links "Integrations" card to the actions reference', () => {
    render(<HomePage />);
    const links = screen.getAllByRole('link');
    const integrationsLink = links.find(
      (l) => l.getAttribute('href') === '/docs/api-reference/actions',
    );
    expect(integrationsLink).toBeDefined();
  });
});
