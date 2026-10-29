import {render, screen} from 'src/test-utils';
import DefaultPermissionsToolbar from './DefaultPermissionsToolbar';

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
  searchOptions: ['Creator'],
  search: {field: 'Creator', query: ''},
  setSearch: vi.fn(),
  setDrawerContent: vi.fn(),
  handleBulkDeleteModalToggle: vi.fn(),
};

describe('DefaultPermissionsToolbar', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockUseSuperuserPermissions.mockReturnValue({isReadOnlySuperUser: false});
  });

  it('shows create button for non-readonly user', () => {
    render(<DefaultPermissionsToolbar {...defaultProps} />);
    expect(
      screen.getByTestId('create-default-permissions-btn'),
    ).toBeInTheDocument();
  });

  it('hides create button for readonly superuser', () => {
    mockUseSuperuserPermissions.mockReturnValue({isReadOnlySuperUser: true});
    render(<DefaultPermissionsToolbar {...defaultProps} />);
    expect(
      screen.queryByTestId('create-default-permissions-btn'),
    ).not.toBeInTheDocument();
  });

  it('hides bulk delete for readonly superuser', () => {
    mockUseSuperuserPermissions.mockReturnValue({isReadOnlySuperUser: true});
    render(
      <DefaultPermissionsToolbar
        {...defaultProps}
        selectedItems={[{id: 1} as never]}
      />,
    );
    expect(
      screen.queryByTestId('default-perm-bulk-delete-icon'),
    ).not.toBeInTheDocument();
  });
});
