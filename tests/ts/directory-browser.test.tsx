import { act, fireEvent, render, screen, within } from '@testing-library/react';
import {
  DirectoryBrowser,
  type DirectoryGroup,
  type DirectoryItem,
} from '@/components/directory-browser';

jest.mock('next/link', () => {
  const MockLink = ({ href, children, ...rest }: { href: string; children: React.ReactNode }) => (
    <a href={href} {...rest}>
      {children}
    </a>
  );
  MockLink.displayName = 'MockLink';
  return { __esModule: true, default: MockLink };
});

jest.mock('next/image', () => {
  // eslint-disable-next-line @next/next/no-img-element
  const MockImage = ({ src, alt }: { src: string; alt: string }) => <img src={src} alt={alt} />;
  MockImage.displayName = 'MockImage';
  return { __esModule: true, default: MockImage };
});

const items: DirectoryItem[] = [
  { id: 'skipflow_review', name: 'Approvals', description: 'Pause until someone approves.', href: '/docs/integrations/built-in/review', actions: 1, builtIn: true },
  { id: 'airtable', name: 'Airtable', description: 'Create and update records in bases.', href: '/docs/integrations/airtable', actions: 12, builtIn: false, categories: ['Spreadsheets'] },
  { id: 'gmail', name: 'Gmail', description: 'Send, read, and manage email.', href: '/docs/integrations/gmail', actions: 14, builtIn: false, logo: 'https://www.lodol.com/app-icons/gmail-icon.png', categories: ['Email', 'Google'], triggers: 1 },
  { id: 'google_sheets', name: 'Google Sheets', description: 'Read and write rows.', href: '/docs/integrations/google-sheets', actions: 18, builtIn: false, categories: ['Spreadsheets', 'Google'] },
  { id: 'notificacion', name: 'Notificación', description: 'Send a notification.', href: '/docs/integrations/notificacion', actions: 1, builtIn: false },
  { id: '_7shifts', name: '7shifts', description: 'Schedule staff.', href: '/docs/integrations/7shifts', actions: 3, builtIn: false },
];

// In lodol.com's order: App Families first.
const groups: DirectoryGroup[] = [
  { key: 'app_families', label: 'App Families', categories: ['Google'] },
  { key: 'communication', label: 'Communication', categories: ['Email'] },
  { key: 'productivity', label: 'Productivity', categories: ['Spreadsheets'] },
];

function renderDirectory() {
  return render(
    <DirectoryBrowser
      items={items}
      popular={['gmail', 'missing', 'google_sheets']}
      groups={groups}
      apps={5}
    />,
  );
}

function choose(label: string) {
  act(() => {
    fireEvent.click(screen.getByRole('button', { name: label }));
  });
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
    expect(screen.getAllByText('18 actions').length).toBeGreaterThan(0);
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

  it("shows an app's logo, or its initials when it has none", () => {
    renderDirectory();
    // The logo is decorative: the app's name is right beside it.
    const gmail = screen.getAllByRole('link', { name: /Gmail/ })[0];
    expect(gmail.querySelector('img')).toHaveAttribute(
      'src',
      'https://www.lodol.com/app-icons/gmail-icon.png',
    );
    expect(gmail.querySelector('img')).toHaveAttribute('alt', '');
    search('airtable');
    expect(within(screen.getByRole('link', { name: /Airtable/ })).getByText('A')).toBeInTheDocument();
  });

  it('counts an app’s triggers beside its actions', () => {
    renderDirectory();
    expect(screen.getAllByText('14 actions · 1 trigger').length).toBeGreaterThan(0);
  });

  it('offers every category group, with app families last', () => {
    renderDirectory();
    const chips = within(screen.getByRole('group', { name: 'Categories' })).getAllByRole('button');
    expect(chips.map((c) => c.textContent)).toEqual([
      'All',
      'Communication',
      'Productivity',
      'App Families',
    ]);
    expect(chips[0]).toHaveAttribute('aria-pressed', 'true');
  });

  it("lists a group's apps by category, most popular first", () => {
    renderDirectory();
    choose('Productivity');
    expect(screen.getByRole('button', { name: 'Productivity' })).toHaveAttribute('aria-pressed', 'true');
    expect(screen.getByText('Productivity: 2 apps')).toBeInTheDocument();
    const section = screen.getByRole('region', { name: 'Spreadsheets' });
    expect(within(section).getAllByRole('link').map((l) => l.getAttribute('href'))).toEqual([
      '/docs/integrations/google-sheets',
      '/docs/integrations/airtable',
    ]);
    expect(screen.queryByRole('heading', { name: 'Built-in steps' })).not.toBeInTheDocument();
  });

  it('searches within the chosen group', () => {
    renderDirectory();
    choose('Communication');
    search('sheets');
    expect(screen.getByText('Nothing in Communication matches “sheets”.')).toBeInTheDocument();
    search('mail');
    expect(screen.getByText('1 match in Communication')).toBeInTheDocument();
  });

  it('finds apps by category', () => {
    renderDirectory();
    search('spreadsheets');
    expect(screen.getByText('2 matches')).toBeInTheDocument();
  });

  it('returns to every app', () => {
    renderDirectory();
    choose('Communication');
    choose('All');
    expect(screen.getByRole('heading', { name: 'Popular apps' })).toBeInTheDocument();
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
