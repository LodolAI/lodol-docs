import { act, fireEvent, render, screen, within } from '@testing-library/react';
import { DirectoryBrowser, type DirectoryItem } from '@/components/directory-browser';

jest.mock('next/link', () => {
  const MockLink = ({ href, children, ...rest }: { href: string; children: React.ReactNode }) => (
    <a href={href} {...rest}>
      {children}
    </a>
  );
  MockLink.displayName = 'MockLink';
  return { __esModule: true, default: MockLink };
});

const items: DirectoryItem[] = [
  { id: 'skipflow_review', name: 'Approvals', description: 'Pause until someone approves.', href: '/docs/integrations/built-in/review', actions: 1, builtIn: true },
  { id: 'airtable', name: 'Airtable', description: 'Create and update records in bases.', href: '/docs/integrations/airtable', actions: 12, builtIn: false },
  { id: 'gmail', name: 'Gmail', description: 'Send, read, and manage email.', href: '/docs/integrations/gmail', actions: 14, builtIn: false },
  { id: 'google_sheets', name: 'Google Sheets', description: 'Read and write rows.', href: '/docs/integrations/google-sheets', actions: 18, builtIn: false },
  { id: 'notificacion', name: 'Notificación', description: 'Send a notification.', href: '/docs/integrations/notificacion', actions: 1, builtIn: false },
  { id: '_7shifts', name: '7shifts', description: 'Schedule staff.', href: '/docs/integrations/7shifts', actions: 3, builtIn: false },
];

function renderDirectory() {
  return render(<DirectoryBrowser items={items} popular={['gmail', 'missing']} apps={5} />);
}

function search(text: string) {
  act(() => {
    fireEvent.change(screen.getByLabelText('Search integrations'), { target: { value: text } });
  });
}

describe('DirectoryBrowser', () => {
  it('says how many apps there are to search', () => {
    renderDirectory();
    expect(screen.getByLabelText('Search integrations')).toHaveAttribute(
      'placeholder',
      'Search 5 apps and built-in steps',
    );
  });

  it('shows built-in steps, popular apps and every app before a search', () => {
    renderDirectory();
    expect(screen.getByRole('heading', { name: 'Built-in steps' })).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'Popular apps' })).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'All 5 apps' })).toBeInTheDocument();
  });

  it('groups every app by its first letter, with numbers last', () => {
    renderDirectory();
    const nav = screen.getByRole('navigation', { name: 'Apps by letter' });
    expect(within(nav).getAllByRole('link').map((l) => l.textContent)).toEqual([
      'A',
      'G',
      'N',
      '#',
    ]);
  });

  it('counts steps for built-in steps and actions for apps', () => {
    renderDirectory();
    expect(screen.getByText('1 step')).toBeInTheDocument();
    expect(screen.getAllByText('14 actions').length).toBeGreaterThan(0);
  });

  it('finds apps by name, best match first', () => {
    renderDirectory();
    search('g');
    const tiles = screen.getAllByRole('link').map((l) => l.getAttribute('href'));
    expect(tiles.slice(0, 2)).toEqual([
      '/docs/integrations/gmail',
      '/docs/integrations/google-sheets',
    ]);
    expect(screen.queryByRole('heading', { name: 'Popular apps' })).not.toBeInTheDocument();
  });

  it('finds apps by what they do, matching every word', () => {
    renderDirectory();
    search('read rows');
    expect(screen.getByText('1 match')).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /Google Sheets/ })).toBeInTheDocument();
  });

  it('ignores accents and case', () => {
    renderDirectory();
    search('NOTIFICACION');
    expect(screen.getByRole('link', { name: /Notificación/ })).toBeInTheDocument();
  });

  it('suggests Call an API when nothing matches', () => {
    renderDirectory();
    search('zzz');
    expect(screen.getByText('Nothing matches “zzz”.')).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Call an API' })).toHaveAttribute(
      'href',
      '/docs/integrations/built-in/http',
    );
  });

  it('clears the search', () => {
    renderDirectory();
    search('gmail');
    act(() => {
      fireEvent.click(screen.getByRole('button', { name: 'Clear search' }));
    });
    expect(screen.getByLabelText('Search integrations')).toHaveValue('');
    expect(screen.getByRole('heading', { name: 'Popular apps' })).toBeInTheDocument();
  });
});
