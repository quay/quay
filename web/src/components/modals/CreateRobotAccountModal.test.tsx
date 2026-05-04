import {render, screen, userEvent, waitFor} from 'src/test-utils';
import CreateRobotAccountModal from './CreateRobotAccountModal';
import {useCreateRobotAccount} from 'src/hooks/useRobotAccounts';
import {useRepositories} from 'src/hooks/UseRepositories';
import {useOrganizations} from 'src/hooks/UseOrganizations';

vi.mock('src/hooks/useRobotAccounts', () => ({
  useCreateRobotAccount: vi.fn(),
}));

vi.mock('src/hooks/UseRepositories', () => ({
  useRepositories: vi.fn(),
}));

vi.mock('src/hooks/UseOrganizations', () => ({
  useOrganizations: vi.fn(),
}));

const mockUseCreateRobotAccount = vi.mocked(useCreateRobotAccount);
const mockUseRepositories = vi.mocked(useRepositories);
const mockUseOrganizations = vi.mocked(useOrganizations);

function makeProps(overrides = {}) {
  return {
    isModalOpen: true,
    handleModalToggle: vi.fn(),
    orgName: 'testorg',
    teams: [{name: 'team1', role: 'admin', member_count: 3}],
    RepoPermissionDropdownItems: [
      {name: 'Read', description: 'Read access'},
      {name: 'Write', description: 'Write access'},
      {name: 'Admin', description: 'Admin access'},
    ],
    showSuccessAlert: vi.fn(),
    showErrorAlert: vi.fn(),
    ...overrides,
  };
}

beforeEach(() => {
  mockUseCreateRobotAccount.mockReturnValue({
    createNewRobot: vi.fn().mockResolvedValue({name: 'testorg+newrobot'}),
    addRepoPerms: vi.fn().mockResolvedValue({}),
    addTeams: vi.fn().mockResolvedValue({}),
    addDefaultPerms: vi.fn().mockResolvedValue({}),
  } as any);
  mockUseRepositories.mockReturnValue({
    repos: [{name: 'repo1', last_modified: 1000}],
  } as any);
  mockUseOrganizations.mockReturnValue({
    usernames: ['myuser'],
  } as any);
});

describe('CreateRobotAccountModal', () => {
  it('returns null when isModalOpen is false', () => {
    render(<CreateRobotAccountModal {...makeProps({isModalOpen: false})} />);
    expect(
      screen.queryByTestId('create-robot-account-modal'),
    ).not.toBeInTheDocument();
  });

  it('renders wizard with name and description step', () => {
    render(<CreateRobotAccountModal {...makeProps()} />);
    expect(
      screen.getByTestId('create-robot-account-modal'),
    ).toBeInTheDocument();
    expect(
      screen.getByText('Provide robot account name and description'),
    ).toBeInTheDocument();
  });

  it('shows 5 steps for organization namespace', () => {
    render(<CreateRobotAccountModal {...makeProps()} />);
    const nav =
      screen.getByRole('navigation', {name: /Wizard/i}) ||
      screen.getByRole('list');
    expect(
      screen.getAllByText('Robot name and description').length,
    ).toBeGreaterThanOrEqual(1);
    expect(
      screen.getAllByText('Add to team (optional)').length,
    ).toBeGreaterThanOrEqual(1);
    expect(
      screen.getAllByText('Add to repository (optional)').length,
    ).toBeGreaterThanOrEqual(1);
    expect(
      screen.getAllByText('Default permissions (optional)').length,
    ).toBeGreaterThanOrEqual(1);
    expect(
      screen.getAllByText('Review and Finish').length,
    ).toBeGreaterThanOrEqual(1);
  });

  it('shows 3 steps for user namespace', () => {
    mockUseOrganizations.mockReturnValue({
      usernames: ['testorg'],
    } as any);
    render(<CreateRobotAccountModal {...makeProps()} />);
    expect(
      screen.getAllByText('Robot name and description').length,
    ).toBeGreaterThanOrEqual(1);
    expect(
      screen.getAllByText('Add to repository (optional)').length,
    ).toBeGreaterThanOrEqual(1);
    expect(
      screen.getAllByText('Review and Finish').length,
    ).toBeGreaterThanOrEqual(1);
    expect(
      screen.queryByText('Add to team (optional)'),
    ).not.toBeInTheDocument();
  });

  it('has name and description input fields', () => {
    render(<CreateRobotAccountModal {...makeProps()} />);
    expect(screen.getByTestId('robot-wizard-form-name')).toBeInTheDocument();
    expect(
      screen.getByTestId('robot-wizard-form-description'),
    ).toBeInTheDocument();
  });

  it('disables Review and Finish button when name is invalid', () => {
    render(<CreateRobotAccountModal {...makeProps()} />);
    expect(screen.getByTestId('create-robot-submit')).toBeDisabled();
  });
});
