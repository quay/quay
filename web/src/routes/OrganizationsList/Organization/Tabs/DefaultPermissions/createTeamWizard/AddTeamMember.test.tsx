import {render, screen, userEvent} from 'src/test-utils';
import AddTeamMember from './AddTeamMember';
import {ITeamMember} from 'src/hooks/UseMembers';

// Mock sub-components
vi.mock('src/components/modals/robotAccountWizard/NameAndDescription', () => ({
  default: (props: {
    name: string;
    nameHelperText: string;
    validateName: () => boolean;
    setName: (s: string) => void;
    setDescription: (s: string) => void;
    nameLabel: string;
    descriptionLabel: string;
    helperText: string;
    description: string;
  }) => (
    <div data-testid="name-and-description">
      <span data-testid="name-helper-text">{props.nameHelperText}</span>
      <span data-testid="validate-result">{String(props.validateName())}</span>
      <input
        data-testid="robot-name-input"
        value={props.name}
        onChange={(e) => props.setName(e.target.value)}
      />
    </div>
  ),
}));

vi.mock('src/components/ToggleDrawer', () => ({
  default: (props: {
    isExpanded: boolean;
    setIsExpanded: (b: boolean) => void;
    drawerpanelContent: React.ReactNode;
  }) => <div data-testid="toggle-drawer">{props.drawerpanelContent}</div>,
}));

vi.mock(
  'src/routes/OrganizationsList/Organization/Tabs/DefaultPermissions/createTeamWizard/AddTeamToolbar',
  () => ({
    default: (props: {children: React.ReactNode}) => (
      <div data-testid="add-team-toolbar">{props.children}</div>
    ),
  }),
);

// Mock hooks
const mockCreateNewRobot = vi.fn();

vi.mock('src/hooks/useRobotAccounts', () => ({
  useCreateRobotAccount: () => ({
    createNewRobot: mockCreateNewRobot,
  }),
  useFetchRobotAccounts: () => ({
    robots: [],
    error: null,
  }),
}));

const sampleMembers: ITeamMember[] = [
  {name: 'alice', kind: 'user', is_robot: false},
  {name: 'testorg+bot1', kind: 'user', is_robot: true},
];

function makeProps(overrides = {}) {
  return {
    orgName: 'testorg',
    allMembers: sampleMembers,
    tableItems: sampleMembers,
    setTableItems: vi.fn(),
    addedTeamMembers: [],
    setAddedTeamMembers: vi.fn(),
    deletedTeamMembers: [],
    setDeletedTeamMembers: vi.fn(),
    isDrawerExpanded: false,
    setDrawerExpanded: vi.fn(),
    ...overrides,
  };
}

describe('AddTeamMember', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('table view (drawer collapsed)', () => {
    it('renders the team member table', () => {
      render(<AddTeamMember {...makeProps()} />);
      expect(screen.getByText('Team Member')).toBeInTheDocument();
      expect(screen.getByText('Account')).toBeInTheDocument();
    });

    it('displays member names in the table', () => {
      render(<AddTeamMember {...makeProps()} />);
      expect(screen.getByText('alice')).toBeInTheDocument();
      expect(screen.getByText('testorg+bot1')).toBeInTheDocument();
    });

    it('shows account type for each member', () => {
      render(<AddTeamMember {...makeProps()} />);
      expect(screen.getByText('Team member')).toBeInTheDocument();
      expect(screen.getByText('Robot account')).toBeInTheDocument();
    });

    it('renders delete buttons for each member', () => {
      render(<AddTeamMember {...makeProps()} />);
      expect(screen.getByTestId('alice-delete-icon')).toBeInTheDocument();
      expect(
        screen.getByTestId('testorg+bot1-delete-icon'),
      ).toBeInTheDocument();
    });

    it('calls setTableItems and setDeletedTeamMembers when deleting an existing member', async () => {
      const setTableItems = vi.fn();
      const setDeletedTeamMembers = vi.fn();
      render(
        <AddTeamMember
          {...makeProps({setTableItems, setDeletedTeamMembers})}
        />,
      );
      await userEvent.click(screen.getByTestId('alice-delete-icon'));
      expect(setTableItems).toHaveBeenCalled();
      expect(setDeletedTeamMembers).toHaveBeenCalled();
    });
  });

  describe('drawer view (robot creation form)', () => {
    it('renders the robot creation form when drawer is expanded', () => {
      render(<AddTeamMember {...makeProps({isDrawerExpanded: true})} />);
      expect(screen.getByTestId('name-and-description')).toBeInTheDocument();
    });

    it('passes updated helper text with new regex pattern', () => {
      render(<AddTeamMember {...makeProps({isDrawerExpanded: true})} />);
      const helperText = screen.getByTestId('name-helper-text').textContent;
      expect(helperText).toContain(
        '^(?=.{2,255}$)([a-z0-9]+(?:[._-][a-z0-9]+)*)$',
      );
    });

    it('validates robot name using shared validateRobotName (empty name = invalid)', () => {
      render(<AddTeamMember {...makeProps({isDrawerExpanded: true})} />);
      const validateResult = screen.getByTestId('validate-result').textContent;
      expect(validateResult).toBe('false');
    });

    it('disables the Add robot account button when name is empty', () => {
      render(<AddTeamMember {...makeProps({isDrawerExpanded: true})} />);
      const addBtn = screen.getByTestId('create-robot-accnt-drawer-btn');
      expect(addBtn).toBeDisabled();
    });

    it('renders a cancel button in the drawer', () => {
      render(<AddTeamMember {...makeProps({isDrawerExpanded: true})} />);
      expect(screen.getByText('Cancel')).toBeInTheDocument();
    });

    it('calls setDrawerExpanded(false) when cancel is clicked', async () => {
      const setDrawerExpanded = vi.fn();
      render(
        <AddTeamMember
          {...makeProps({isDrawerExpanded: true, setDrawerExpanded})}
        />,
      );
      await userEvent.click(screen.getByText('Cancel'));
      expect(setDrawerExpanded).toHaveBeenCalledWith(false);
    });

    it('renders the Provide a name heading', () => {
      render(<AddTeamMember {...makeProps({isDrawerExpanded: true})} />);
      expect(
        screen.getByText('Provide a name and description'),
      ).toBeInTheDocument();
    });
  });
});
