import {render, screen} from 'src/test-utils';
import MembersViewToolbar from './MembersViewToolbar';

const mockUseSuperuserPermissions = vi.hoisted(() =>
  vi.fn(() => ({isReadOnlySuperUser: false})),
);

vi.mock('src/hooks/UseSuperuserPermissions', () => ({
  useSuperuserPermissions: mockUseSuperuserPermissions,
}));

const defaultProps = {
  selectedMembers: [],
  deSelectAll: vi.fn(),
  allItems: [],
  paginatedItems: [],
  onItemSelect: vi.fn(),
  page: 1,
  setPage: vi.fn(),
  perPage: 10,
  setPerPage: vi.fn(),
  searchOptions: ['User name'],
  search: {field: 'User name', query: ''},
  setSearch: vi.fn(),
  handleModalToggle: vi.fn(),
};

describe('MembersViewToolbar', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockUseSuperuserPermissions.mockReturnValue({isReadOnlySuperUser: false});
  });

  it('shows create team button for non-readonly user', () => {
    render(<MembersViewToolbar {...defaultProps} />);
    expect(screen.getByTestId('create-new-team-button')).toBeInTheDocument();
  });

  it('hides create team button for readonly superuser', () => {
    mockUseSuperuserPermissions.mockReturnValue({isReadOnlySuperUser: true});
    render(<MembersViewToolbar {...defaultProps} />);
    expect(
      screen.queryByTestId('create-new-team-button'),
    ).not.toBeInTheDocument();
  });
});
