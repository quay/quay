import {render, screen} from 'src/test-utils';
import {OrganizationToolBar} from './OrganizationToolBar';

vi.mock('src/hooks/UseSuperuserPermissions', () => ({
  useSuperuserPermissions: () => ({
    canModify: false,
    isReadOnlySuperUser: false,
  }),
}));

vi.mock('./modals/CreateUserModal', () => ({
  CreateUserModal: () => null,
}));

const baseProps = {
  createOrgModal: {},
  isOrganizationModalOpen: false,
  setOrganizationModalOpen: vi.fn(),
  isKebabOpen: false,
  setKebabOpen: vi.fn(),
  kebabItems: [],
  selectedOrganization: [],
  deleteKebabIsOpen: false,
  deleteModal: {},
  organizationsList: [],
  perPage: 10,
  page: 1,
  setPage: vi.fn(),
  setPerPage: vi.fn(),
  total: 0,
  search: {query: '', field: 'name'},
  setSearch: vi.fn(),
  setSelectedOrganization: vi.fn(),
  paginatedOrganizationsList: [],
  onSelectOrganization: vi.fn(),
  isExternalAuth: false,
};

describe('OrganizationToolBar', () => {
  it('hides create button and checkbox for unauthenticated users', () => {
    render(<OrganizationToolBar {...baseProps} isAuthenticated={false} />);
    expect(screen.queryByText('Create Organization')).not.toBeInTheDocument();
  });

  it('shows create button for authenticated users', () => {
    render(<OrganizationToolBar {...baseProps} isAuthenticated={true} />);
    expect(screen.getByText('Create Organization')).toBeInTheDocument();
  });
});
