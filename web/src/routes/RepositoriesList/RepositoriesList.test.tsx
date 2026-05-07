import {render, screen} from 'src/test-utils';
import RepositoriesList from './RepositoriesList';

// Minimal stubs for hooks unrelated to the spinner logic
// Breaks: RepositoriesList → Breadcrumb → NavigationPath → OrganizationsList → Organizations.scss (Sass compat issue in test env)
vi.mock('src/components/breadcrumb/Breadcrumb', () => ({
  QuayBreadcrumb: () => null,
}));

vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom');
  return {
    ...actual,
    useLocation: () => ({pathname: '/repository', search: '', hash: ''}),
    Link: ({children, to}: {children: React.ReactNode; to: string}) => (
      <a href={to}>{children}</a>
    ),
  };
});

vi.mock('src/hooks/UseQuayConfig', () => ({
  useQuayConfig: () => ({
    features: {QUOTA_MANAGEMENT: false, EDIT_QUOTA: false},
  }),
}));

vi.mock('src/hooks/UseCurrentUser', () => ({
  useCurrentUser: () => ({user: {username: 'testuser'}}),
}));

vi.mock('src/hooks/UseSuperuserPermissions', () => ({
  useSuperuserPermissions: () => ({isReadOnlySuperUser: false}),
}));

vi.mock('src/hooks/UseQuotaManagement', () => ({
  useFetchOrganizationQuota: () => ({organizationQuota: null}),
}));

vi.mock('src/hooks/UseDeleteRepositories', () => ({
  useDeleteRepositories: () => ({
    deleteRepositories: vi.fn(),
    errorDeleteRepositories: null,
    successDeleteRepositories: false,
  }),
}));

const mockSetSearch = vi.fn();
const baseReposHook = {
  repos: [
    {namespace: 'testorg', name: 'my-repo', is_public: true, last_modified: 0},
  ],
  loading: false,
  error: null,
  search: {query: '', field: 'name', isRegEx: false},
  setSearch: mockSetSearch,
  searchFilter: null,
  truncated: false,
};

const mockUseRepositories = vi.fn(() => baseReposHook);
vi.mock('src/hooks/UseRepositories', () => ({
  useRepositories: (...args: unknown[]) => mockUseRepositories(...args),
}));

// usePaginatedSortableTable controls filteredData (what the table renders)
const mockPaginatedTable = vi.fn();
vi.mock('../../hooks/usePaginatedSortableTable', () => ({
  usePaginatedSortableTable: (...args: unknown[]) =>
    mockPaginatedTable(...args),
}));

const basePaginatedReturn = {
  filteredData: [],
  paginatedData: [],
  getSortableSort: () => undefined,
  paginationProps: {
    total: 0,
    perPage: 25,
    page: 1,
    setPage: vi.fn(),
    setPerPage: vi.fn(),
  },
};

const oneRepo = {
  namespace: 'testorg',
  name: 'my-repo',
  is_public: true,
  size: 0,
  last_modified: 0,
};

describe('RepositoriesList — search empty state (PROJQUAY-11217)', () => {
  beforeEach(() => {
    mockUseRepositories.mockReturnValue(baseReposHook);
    mockPaginatedTable.mockReturnValue(basePaginatedReturn);
  });

  it('shows a spinner while data is loading', () => {
    mockUseRepositories.mockReturnValue({
      ...baseReposHook,
      loading: true,
      repos: [],
    });
    mockPaginatedTable.mockReturnValue({
      ...basePaginatedReturn,
      filteredData: [],
    });

    render(<RepositoriesList organizationName="testorg" />);

    expect(screen.queryByRole('progressbar')).toBeInTheDocument();
    expect(screen.queryByText('No repositories found')).not.toBeInTheDocument();
  });

  it('shows "No repositories found" when search returns no results (regression: PROJQUAY-11217)', () => {
    // loading=false, repos has items, but the filter matched nothing → filteredData=[]
    mockUseRepositories.mockReturnValue({
      ...baseReposHook,
      loading: false,
      repos: [
        {
          namespace: 'testorg',
          name: 'my-repo',
          is_public: true,
          last_modified: 0,
        },
      ],
    });
    mockPaginatedTable.mockReturnValue({
      ...basePaginatedReturn,
      filteredData: [],
    });

    render(<RepositoriesList organizationName="testorg" />);

    expect(screen.getByText('No repositories found')).toBeInTheDocument();
    expect(screen.queryByRole('progressbar')).not.toBeInTheDocument();
  });

  it('renders repository rows when results are present', () => {
    mockUseRepositories.mockReturnValue({...baseReposHook, loading: false});
    mockPaginatedTable.mockReturnValue({
      ...basePaginatedReturn,
      filteredData: [oneRepo],
      paginatedData: [oneRepo],
    });

    render(<RepositoriesList organizationName="testorg" />);

    expect(screen.getByText('my-repo')).toBeInTheDocument();
    expect(screen.queryByRole('progressbar')).not.toBeInTheDocument();
    expect(screen.queryByText('No repositories found')).not.toBeInTheDocument();
  });
});
