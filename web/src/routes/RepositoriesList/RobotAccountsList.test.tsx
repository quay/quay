import {render, screen, userEvent, within} from 'src/test-utils';
import {formatDate} from 'src/libs/utils';
import {IRobot} from 'src/resources/RobotsResource';
import RobotAccountsList from './RobotAccountsList';

const robotsMock = vi.hoisted(() => ({
  robots: [] as IRobot[],
}));

vi.mock('src/hooks/useRobotAccounts', () => ({
  useRobotAccounts: () => ({robotAccountsForOrg: robotsMock.robots}),
  useRobotRepoPermissions: () => ({
    updateRepoPerms: vi.fn(),
    deleteRepoPerms: vi.fn(),
  }),
}));

vi.mock('src/hooks/UseDeleteRobotAccount', () => ({
  useDeleteRobotAccounts: () => ({deleteRobotAccounts: vi.fn()}),
}));

vi.mock('src/hooks/UseQuayConfig', () => ({
  useQuayConfig: () => ({config: {}, features: {}}),
}));

vi.mock('src/resources/OrganizationResource', () => ({
  fetchOrg: vi.fn().mockResolvedValue({teams: {}}),
}));

vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom');
  return {
    ...actual,
    Link: ({children, to}: {children: React.ReactNode; to: string}) => (
      <a href={to}>{children}</a>
    ),
  };
});

// The API returns RFC 2822 timestamps for both created and last_accessed.
const LAST_ACCESSED_RAW = 'Mon, 19 Oct 2026 19:18:34 -0000';
const CREATED_RAW = 'Mon, 19 Oct 2026 18:45:12 -0000';

const makeRobot = (overrides: Partial<IRobot> & {name: string}): IRobot => ({
  created: CREATED_RAW,
  last_accessed: null,
  teams: [],
  repositories: [],
  description: '',
  ...overrides,
});

const props = {organizationName: 'testorg', isUser: false};

// PatternFly's Td exposes its column as data-label, which is how the
// responsive layout labels each cell.
const cell = (row: HTMLElement, column: string): HTMLElement =>
  row.querySelector(`td[data-label="${column}"]`);

function cellsFor(robotName: string) {
  const row = within(screen.getByTestId('robot-accounts-table'))
    .getByText(robotName)
    .closest('tr');
  return {
    lastAccessed: cell(row, 'Last accessed'),
    created: cell(row, 'Created'),
  };
}

describe('RobotAccountsList last accessed column', () => {
  beforeEach(() => {
    robotsMock.robots = [];
  });

  it('formats last accessed the same way as created', async () => {
    robotsMock.robots = [
      makeRobot({name: 'testorg+used', last_accessed: LAST_ACCESSED_RAW}),
    ];
    render(<RobotAccountsList {...props} />);

    await screen.findByText('testorg+used');
    const {lastAccessed, created} = cellsFor('testorg+used');

    expect(created).toHaveTextContent(formatDate(CREATED_RAW));
    expect(lastAccessed).toHaveTextContent(formatDate(LAST_ACCESSED_RAW));
    expect(lastAccessed).not.toHaveTextContent(LAST_ACCESSED_RAW);
  });

  it('shows Never when the robot was never used', async () => {
    robotsMock.robots = [
      makeRobot({name: 'testorg+unused', last_accessed: null}),
      makeRobot({name: 'testorg+blank', last_accessed: ''}),
    ];
    render(<RobotAccountsList {...props} />);

    await screen.findByText('testorg+unused');
    expect(cellsFor('testorg+unused').lastAccessed).toHaveTextContent(
      /^Never$/,
    );
    expect(cellsFor('testorg+blank').lastAccessed).toHaveTextContent(/^Never$/);
  });

  it('sorts by last accessed with never-used robots first', async () => {
    const user = userEvent.setup();
    robotsMock.robots = [
      makeRobot({
        name: 'testorg+newer',
        last_accessed: 'Tue, 20 Oct 2026 08:00:00 -0000',
      }),
      makeRobot({name: 'testorg+never', last_accessed: null}),
      makeRobot({
        name: 'testorg+older',
        last_accessed: 'Sun, 18 Oct 2026 08:00:00 -0000',
      }),
    ];
    render(<RobotAccountsList {...props} />);
    await screen.findByText('testorg+never');

    await user.click(screen.getByRole('button', {name: /^Last accessed/}));

    const names = Array.from(
      screen
        .getByTestId('robot-accounts-table')
        .querySelectorAll('td[data-label="Robot account name"]'),
    ).map((nameCell) => nameCell.textContent.trim());
    expect(names).toEqual(['testorg+never', 'testorg+older', 'testorg+newer']);
  });
});
