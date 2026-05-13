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

  it('exposes both primary calls to action', () => {
    render(<HomePage />);
    expect(screen.getAllByRole('link')).toHaveLength(2);
  });
});
