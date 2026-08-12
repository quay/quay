import {render, screen, userEvent} from 'src/test-utils';
import {MemoryRouter, Route, Routes} from 'react-router-dom';
import ManageMembersList from './ManageMembersList';

const mockRemoveTeamMember = vi.fn();
const mockRemoveEmailInvite = vi.fn();

vi.mock('src/hooks/UseMembers', () => ({
  useFetchTeamMembersForOrg: () => ({
    allMembers: [
      {name: 'alice', kind: 'user', is_robot: false, invited: false},
      {
        name: 'testorg+bot1',
        kind: 'user',
        is_robot: true,
        invited: false,
      },
      {
        email: 'invited@example.com',
        kind: 'invite',
        is_robot: false,
        invited: true,
      },
    ],
    teamMembers: [
      {name: 'alice', kind: 'user', is_robot: false, invited: false},
    ],
    robotAccounts: [
      {
        name: 'testorg+bot1',
        kind: 'user',
        is_robot: true,
        invited: false,
      },
    ],
    invited: [
      {
        email: 'invited@example.com',
        kind: 'invite',
        is_robot: false,
        invited: true,
      },
    ],
    teamCanSync: null,
    teamSyncInfo: null,
    loading: false,
    search: {query: '', field: 'teamMember'},
    setSearch: vi.fn(),
  }),
  useDeleteTeamMember: () => ({
    removeTeamMember: mockRemoveTeamMember,
    errorDeleteTeamMember: false,
    successDeleteTeamMember: false,
    resetDeleteTeamMember: vi.fn(),
  }),
  useDeleteEmailInvite: () => ({
    removeEmailInvite: mockRemoveEmailInvite,
    errorDeleteEmailInvite: false,
    successDeleteEmailInvite: false,
    resetDeleteEmailInvite: vi.fn(),
  }),
}));

vi.mock('src/hooks/UseTeams', () => ({
  useFetchTeams: () => ({teams: [{name: 'testteam', role: 'member'}]}),
  useUpdateTeamDetails: () => ({
    updateTeamDetails: vi.fn(),
    errorUpdatingTeam: false,
    successUpdatingTeam: false,
    resetUpdateTeam: vi.fn(),
  }),
}));

vi.mock('src/hooks/UseQuayConfig', () => ({
  useQuayConfig: () => ({
    registry_state: 'normal',
    features: {MAILING: true},
    config: {REGISTRY_TITLE_SHORT: 'Quay'},
  }),
}));

vi.mock('src/hooks/UseOrganization', () => ({
  useOrganization: () => ({
    organization: {is_admin: true},
  }),
}));

vi.mock('src/hooks/UseTeamSync', () => ({
  useTeamSync: () => ({
    enableTeamSync: vi.fn(),
    isError: false,
    isSuccess: false,
  }),
  useRemoveTeamSync: () => ({
    removeTeamSync: vi.fn(),
    isError: false,
    isSuccess: false,
  }),
}));

vi.mock('src/components/modals/DirectoryTeamSyncModal', () => ({
  default: () => null,
}));

vi.mock('src/components/modals/ConfirmationModal', () => ({
  ConfirmationModal: () => null,
}));

vi.mock('./ManageMembersToolbar', () => ({
  default: ({children}: {children: React.ReactNode}) => <div>{children}</div>,
}));

vi.mock('src/components/modals/DeleteModalForRowTemplate', () => ({
  default: ({
    isModalOpen,
    deleteHandler,
    itemToBeDeleted,
  }: {
    isModalOpen: boolean;
    deleteHandler: (item: any) => void;
    itemToBeDeleted: any;
  }) =>
    isModalOpen ? (
      <div data-testid="delete-modal">
        <span data-testid="delete-modal-member">
          {itemToBeDeleted?.memberName}
        </span>
        <button
          data-testid="delete-modal-confirm"
          onClick={() => deleteHandler(itemToBeDeleted)}
        />
      </div>
    ) : null,
}));

vi.mock('src/components/empty/Conditional', () => ({
  default: ({
    if: condition,
    children,
  }: {
    if: boolean;
    children: React.ReactNode;
  }) => (condition ? <>{children}</> : null),
}));

vi.mock('src/components/empty/Empty', () => ({
  default: () => <div>Empty</div>,
}));

vi.mock('src/resources/TeamSyncResource', () => ({
  SupportedService: {},
}));

function renderManageMembersList() {
  return render(
    <MemoryRouter
      initialEntries={[
        '/organization/testorg/teams/testteam?tab=Teamsandmembership',
      ]}
    >
      <Routes>
        <Route
          path="/organization/:organizationName/teams/:teamName"
          element={<ManageMembersList />}
        />
      </Routes>
    </MemoryRouter>,
  );
}

describe('ManageMembersList', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('displays email for invited members in the table', () => {
    renderManageMembersList();
    expect(screen.getByTestId('invited@example.com')).toBeInTheDocument();
    expect(screen.getByText('invited@example.com')).toBeInTheDocument();
  });

  it('displays username for regular members', () => {
    renderManageMembersList();
    expect(screen.getByTestId('alice')).toBeInTheDocument();
    expect(screen.getByText('alice')).toBeInTheDocument();
  });

  it('shows (Invited) account type for email invites', () => {
    renderManageMembersList();
    expect(screen.getByText('(Invited)')).toBeInTheDocument();
  });

  it('renders all view mode toggle buttons', () => {
    renderManageMembersList();
    expect(screen.getByTestId('All Members')).toBeInTheDocument();
    expect(screen.getByTestId('Team Member')).toBeInTheDocument();
    expect(screen.getByTestId('Robot Accounts')).toBeInTheDocument();
    expect(screen.getByTestId('Invited')).toBeInTheDocument();
  });

  it('shows robot account in table with correct account type', () => {
    renderManageMembersList();
    expect(screen.getByTestId('testorg+bot1')).toBeInTheDocument();
    expect(screen.getByText('Robot account')).toBeInTheDocument();
  });

  it('opens delete modal for invited member and confirms calls removeEmailInvite', async () => {
    renderManageMembersList();
    await userEvent.click(
      screen.getByTestId('invited@example.com-delete-icon'),
    );
    expect(screen.getByTestId('delete-modal')).toBeInTheDocument();
    expect(screen.getByTestId('delete-modal-member')).toHaveTextContent(
      'invited@example.com',
    );
    await userEvent.click(screen.getByTestId('delete-modal-confirm'));
    expect(mockRemoveEmailInvite).toHaveBeenCalledWith({
      teamName: 'testteam',
      email: 'invited@example.com',
    });
    expect(mockRemoveTeamMember).not.toHaveBeenCalled();
  });

  it('opens delete modal for regular member and confirms calls removeTeamMember', async () => {
    renderManageMembersList();
    await userEvent.click(screen.getByTestId('alice-delete-icon'));
    expect(screen.getByTestId('delete-modal')).toBeInTheDocument();
    expect(screen.getByTestId('delete-modal-member')).toHaveTextContent(
      'alice',
    );
    await userEvent.click(screen.getByTestId('delete-modal-confirm'));
    expect(mockRemoveTeamMember).toHaveBeenCalledWith({
      teamName: 'testteam',
      memberName: 'alice',
    });
    expect(mockRemoveEmailInvite).not.toHaveBeenCalled();
  });
});
