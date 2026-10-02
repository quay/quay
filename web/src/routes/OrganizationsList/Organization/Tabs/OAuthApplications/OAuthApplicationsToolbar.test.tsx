import {render, screen} from 'src/test-utils';
import OAuthApplicationsToolbar from './OAuthApplicationsToolbar';

const mockUseSuperuserPermissions = vi.hoisted(() =>
  vi.fn(() => ({isReadOnlySuperUser: false})),
);

vi.mock('src/hooks/UseSuperuserPermissions', () => ({
  useSuperuserPermissions: mockUseSuperuserPermissions,
}));

const defaultProps = {
  selectedItems: [],
  deSelectAll: vi.fn(),
  allItems: [],
  paginatedItems: [],
  onItemSelect: vi.fn(),
  page: 1,
  setPage: vi.fn(),
  perPage: 10,
  setPerPage: vi.fn(),
  searchOptions: ['Name'],
  search: {field: 'Name', query: ''},
  setSearch: vi.fn(),
  handleCreateModalToggle: vi.fn(),
  handleBulkDeleteModalToggle: vi.fn(),
};

describe('OAuthApplicationsToolbar', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockUseSuperuserPermissions.mockReturnValue({isReadOnlySuperUser: false});
  });

  it('shows create button for non-readonly user', () => {
    render(<OAuthApplicationsToolbar {...defaultProps} />);
    expect(
      screen.getByTestId('create-oauth-application-button'),
    ).toBeInTheDocument();
  });

  it('hides create button for readonly superuser', () => {
    mockUseSuperuserPermissions.mockReturnValue({isReadOnlySuperUser: true});
    render(<OAuthApplicationsToolbar {...defaultProps} />);
    expect(
      screen.queryByTestId('create-oauth-application-button'),
    ).not.toBeInTheDocument();
  });

  it('hides bulk delete for readonly superuser', () => {
    mockUseSuperuserPermissions.mockReturnValue({isReadOnlySuperUser: true});
    render(
      <OAuthApplicationsToolbar
        {...defaultProps}
        selectedItems={[{name: 'test'} as never]}
      />,
    );
    expect(
      screen.queryByTestId('default-perm-bulk-delete-icon'),
    ).not.toBeInTheDocument();
  });
});
