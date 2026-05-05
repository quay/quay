import {render, screen, waitFor} from 'src/test-utils';
import userEvent from '@testing-library/user-event';
import OAuthApplicationsList from './OAuthApplicationsList';
import {
  useBulkDeleteOAuthApplications,
  useFetchOAuthApplications,
  IOAuthApplication,
} from 'src/hooks/UseOAuthApplications';

vi.mock('src/hooks/UseOAuthApplications', () => ({
  useFetchOAuthApplications: vi.fn(),
  useBulkDeleteOAuthApplications: vi.fn(),
}));

vi.mock('./CreateOAuthApplicationModal', () => ({
  default: () => null,
}));

vi.mock('./ManageOAuthApplicationDrawer', () => ({
  default: ({children}: {children: React.ReactNode}) => <>{children}</>,
}));

vi.mock('./OAuthApplicationActionsKebab', () => ({
  default: () => null,
}));

function makeApp(
  overrides: Partial<IOAuthApplication> = {},
): IOAuthApplication {
  return {
    name: 'app',
    client_id: 'cid-1',
    client_secret: 'secret',
    application_uri: 'https://example.com',
    redirect_uri: 'https://example.com/callback',
    avatar_email: '',
    description: '',
    ...overrides,
  };
}

function mockFetchHook(apps: IOAuthApplication[]) {
  vi.mocked(useFetchOAuthApplications).mockReturnValue({
    loading: false,
    errorLoadingOAuthApplications: false,
    oauthApplications: apps,
    paginatedOAuthApplications: apps,
    filteredOAuthApplications: apps,
    page: 1,
    setPage: vi.fn(),
    perPage: 20,
    setPerPage: vi.fn(),
    search: {query: '', field: 'Application Name'},
    setSearch: vi.fn(),
  });
}

function mockBulkDeleteHook() {
  const bulkDeleteFn = vi.fn();
  vi.mocked(useBulkDeleteOAuthApplications).mockReturnValue({
    bulkDeleteOAuthApplications: bulkDeleteFn,
  });
  return bulkDeleteFn;
}

function getRowCheckbox(rowIndex: number): HTMLElement {
  return screen.getByRole('checkbox', {name: `Select row ${rowIndex}`});
}

describe('OAuthApplicationsList', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders the table with applications', () => {
    const apps = [
      makeApp({name: 'MyApp', client_id: 'abc123'}),
      makeApp({name: 'OtherApp', client_id: 'def456'}),
    ];
    mockFetchHook(apps);
    mockBulkDeleteHook();

    render(<OAuthApplicationsList orgName="myorg" />);

    expect(screen.getByText('MyApp')).toBeInTheDocument();
    expect(screen.getByText('OtherApp')).toBeInTheDocument();
  });

  it('selects individual applications by clicking row checkboxes', async () => {
    const apps = [
      makeApp({name: 'App1', client_id: 'cid-1'}),
      makeApp({name: 'App2', client_id: 'cid-2'}),
    ];
    mockFetchHook(apps);
    mockBulkDeleteHook();

    render(<OAuthApplicationsList orgName="myorg" />);

    await userEvent.click(getRowCheckbox(0));
    await userEvent.click(getRowCheckbox(1));

    expect(getRowCheckbox(0)).toBeChecked();
    expect(getRowCheckbox(1)).toBeChecked();
  });

  it('selects apps with duplicate names independently using client_id', async () => {
    const apps = [
      makeApp({name: 'SameName', client_id: 'cid-aaa'}),
      makeApp({name: 'SameName', client_id: 'cid-bbb'}),
      makeApp({name: 'SameName', client_id: 'cid-ccc'}),
    ];
    mockFetchHook(apps);
    mockBulkDeleteHook();

    render(<OAuthApplicationsList orgName="myorg" />);

    await userEvent.click(getRowCheckbox(0));
    await userEvent.click(getRowCheckbox(1));
    await userEvent.click(getRowCheckbox(2));

    expect(getRowCheckbox(0)).toBeChecked();
    expect(getRowCheckbox(1)).toBeChecked();
    expect(getRowCheckbox(2)).toBeChecked();
  });

  it('deselects one duplicate-named app without affecting the other', async () => {
    const apps = [
      makeApp({name: 'SameName', client_id: 'cid-aaa'}),
      makeApp({name: 'SameName', client_id: 'cid-bbb'}),
    ];
    mockFetchHook(apps);
    mockBulkDeleteHook();

    render(<OAuthApplicationsList orgName="myorg" />);

    await userEvent.click(getRowCheckbox(0));
    await userEvent.click(getRowCheckbox(1));

    expect(getRowCheckbox(0)).toBeChecked();
    expect(getRowCheckbox(1)).toBeChecked();

    await userEvent.click(getRowCheckbox(0));

    expect(getRowCheckbox(0)).not.toBeChecked();
    expect(getRowCheckbox(1)).toBeChecked();
  });

  it('passes all selected duplicate-named apps to bulk delete', async () => {
    const apps = [
      makeApp({name: 'SameName', client_id: 'cid-aaa'}),
      makeApp({name: 'SameName', client_id: 'cid-bbb'}),
    ];
    mockFetchHook(apps);
    const bulkDeleteFn = mockBulkDeleteHook();

    render(<OAuthApplicationsList orgName="myorg" />);

    await userEvent.click(getRowCheckbox(0));
    await userEvent.click(getRowCheckbox(1));

    const deleteButton = screen.getByTestId('default-perm-bulk-delete-icon');
    await userEvent.click(deleteButton);

    await waitFor(() => {
      expect(screen.getByTestId('bulk-delete-modal')).toBeInTheDocument();
    });

    const confirmInput = screen.getByTestId('delete-confirmation-input');
    await userEvent.type(confirmInput, 'confirm');

    const confirmButton = screen.getByTestId('bulk-delete-confirm-btn');
    await userEvent.click(confirmButton);

    await waitFor(() => {
      expect(bulkDeleteFn).toHaveBeenCalledWith(
        expect.arrayContaining([
          expect.objectContaining({client_id: 'cid-aaa'}),
          expect.objectContaining({client_id: 'cid-bbb'}),
        ]),
      );
    });
    expect(bulkDeleteFn.mock.calls[0][0]).toHaveLength(2);
  });

  it('shows empty state when no applications exist', () => {
    mockFetchHook([]);
    mockBulkDeleteHook();

    render(<OAuthApplicationsList orgName="myorg" />);

    expect(
      screen.getByText(
        "This organization doesn't have any OAuth applications defined.",
      ),
    ).toBeInTheDocument();
  });

  it('shows error state when loading fails', () => {
    vi.mocked(useFetchOAuthApplications).mockReturnValue({
      loading: false,
      errorLoadingOAuthApplications: true,
      oauthApplications: [],
      paginatedOAuthApplications: [],
      filteredOAuthApplications: [],
      page: 1,
      setPage: vi.fn(),
      perPage: 20,
      setPerPage: vi.fn(),
      search: {query: '', field: 'Application Name'},
      setSearch: vi.fn(),
    });
    mockBulkDeleteHook();

    render(<OAuthApplicationsList orgName="myorg" />);

    expect(
      screen.getByText('Unable to load OAuth Applications'),
    ).toBeInTheDocument();
  });
});
