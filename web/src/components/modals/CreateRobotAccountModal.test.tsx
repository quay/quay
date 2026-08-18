import {render, screen} from 'src/test-utils';
import CreateRobotAccountModal from './CreateRobotAccountModal';

// Mock heavy sub-components that are not under test
const componentMocks = vi.hoisted(() => ({
  nameAndDescription: vi.fn((props) => (
    <div data-testid="name-and-description">
      <span data-testid="name-helper-text">{props.nameHelperText}</span>
      <span data-testid="validate-result">{String(props.validateName())}</span>
    </div>
  )),
  footer: vi.fn((props) => (
    <div data-testid="footer">
      <span data-testid="footer-valid">{String(props.isDataValid())}</span>
    </div>
  )),
  addToTeam: vi.fn(() => <div data-testid="add-to-team" />),
  addToRepository: vi.fn(() => <div data-testid="add-to-repo" />),
  defaultPermissions: vi.fn(() => <div data-testid="default-permissions" />),
  reviewAndFinish: vi.fn(() => <div data-testid="review-and-finish" />),
}));

vi.mock('./robotAccountWizard/NameAndDescription', () => ({
  default: componentMocks.nameAndDescription,
}));

vi.mock('./robotAccountWizard/Footer', () => ({
  default: componentMocks.footer,
}));

vi.mock('./robotAccountWizard/AddToTeam', () => ({
  default: componentMocks.addToTeam,
}));

vi.mock('./robotAccountWizard/AddToRepository', () => ({
  default: componentMocks.addToRepository,
}));

vi.mock('./robotAccountWizard/DefaultPermissions', () => ({
  default: componentMocks.defaultPermissions,
}));

vi.mock('./robotAccountWizard/ReviewAndFinish', () => ({
  default: componentMocks.reviewAndFinish,
}));

// Mock hooks with controllable return values
const mockUseOrganizations = vi.hoisted(() =>
  vi.fn(() => ({usernames: [] as string[]})),
);

vi.mock('src/hooks/useRobotAccounts', () => ({
  useCreateRobotAccount: () => ({
    createNewRobot: vi.fn(),
    addRepoPerms: vi.fn(),
    addTeams: vi.fn(),
    addDefaultPerms: vi.fn(),
  }),
}));

vi.mock('src/hooks/UseRepositories', () => ({
  useRepositories: () => ({repos: []}),
}));

vi.mock('src/hooks/UseOrganizations', () => ({
  useOrganizations: (...args: unknown[]) => mockUseOrganizations(...args),
}));

function makeProps(overrides = {}) {
  return {
    isModalOpen: true,
    handleModalToggle: vi.fn(),
    orgName: 'testorg',
    teams: [],
    RepoPermissionDropdownItems: [],
    showSuccessAlert: vi.fn(),
    showErrorAlert: vi.fn(),
    ...overrides,
  };
}

describe('CreateRobotAccountModal', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockUseOrganizations.mockReturnValue({usernames: []});
  });

  it('returns null when modal is closed', () => {
    const {container} = render(
      <CreateRobotAccountModal {...makeProps({isModalOpen: false})} />,
    );
    expect(container.innerHTML).toBe('');
  });

  it('renders the wizard when modal is open', () => {
    render(<CreateRobotAccountModal {...makeProps()} />);
    expect(
      screen.getByText('Create robot account (organization/namespace)'),
    ).toBeInTheDocument();
  });

  it('renders the NameAndDescription step', () => {
    render(<CreateRobotAccountModal {...makeProps()} />);
    expect(screen.getByTestId('name-and-description')).toBeInTheDocument();
  });

  it('passes updated helper text with new regex pattern to NameAndDescription', () => {
    render(<CreateRobotAccountModal {...makeProps()} />);
    const helperText = screen.getByTestId('name-helper-text').textContent;
    expect(helperText).toContain(
      '^(?=.{2,255}$)([a-z0-9]+(?:[._-][a-z0-9]+)*)$',
    );
  });

  it('validates robot name using the shared validateRobotName utility', () => {
    // The component starts with an empty robotName state, so validation
    // should return false (empty string fails the regex).
    render(<CreateRobotAccountModal {...makeProps()} />);
    const validateResult = screen.getByTestId('validate-result').textContent;
    expect(validateResult).toBe('false');
  });

  it('passes isDataValid to Footer using validateRobotName', () => {
    render(<CreateRobotAccountModal {...makeProps()} />);
    // Footer receives isDataValid which calls validateRobotName with the
    // current (empty) robotName state — should be false.
    const footerValid = screen.getByTestId('footer-valid').textContent;
    expect(footerValid).toBe('false');
  });

  it('includes team and default-permission wizard steps for org namespaces', () => {
    mockUseOrganizations.mockReturnValue({usernames: []});
    render(<CreateRobotAccountModal {...makeProps()} />);
    // PF Wizard renders nav buttons for all steps. Org wizard includes
    // "Add to team" and "Default permissions".
    expect(
      screen.getByRole('button', {name: 'Add to team (optional)'}),
    ).toBeInTheDocument();
    expect(
      screen.getByRole('button', {name: 'Default permissions (optional)'}),
    ).toBeInTheDocument();
  });

  it('omits team and default-permission steps for user namespaces', () => {
    mockUseOrganizations.mockReturnValue({usernames: ['testorg']});
    render(<CreateRobotAccountModal {...makeProps()} />);
    // User wizard omits "Add to team" and "Default permissions"
    expect(
      screen.queryByRole('button', {name: 'Add to team (optional)'}),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByRole('button', {name: 'Default permissions (optional)'}),
    ).not.toBeInTheDocument();
    // But still has core steps
    expect(
      screen.getByRole('button', {name: 'Robot name and description'}),
    ).toBeInTheDocument();
    expect(
      screen.getByRole('button', {name: 'Review and Finish'}),
    ).toBeInTheDocument();
  });

  it('renders the Footer component', () => {
    render(<CreateRobotAccountModal {...makeProps()} />);
    expect(screen.getByTestId('footer')).toBeInTheDocument();
  });
});
