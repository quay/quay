import {screen, render, userEvent, waitFor} from 'src/test-utils';
import RobotAPITokensTab from './RobotAPITokensTab';

const resourceMocks = vi.hoisted(() => ({
  create: vi.fn(),
  fetch: vi.fn(),
  fetchMintableScopes: vi.fn(),
  revoke: vi.fn(),
}));

vi.mock('src/resources/RobotsResource', async () => {
  const actual = await vi.importActual('src/resources/RobotsResource');
  return {
    ...actual,
    createRobotAPIToken: resourceMocks.create,
    fetchRobotAPITokens: resourceMocks.fetch,
    fetchRobotMintableScopes: resourceMocks.fetchMintableScopes,
    revokeRobotAPIToken: resourceMocks.revoke,
  };
});

const props = {
  namespace: 'testorg',
  robotName: 'testorg+robot',
  isUserOrganization: false,
};

describe('RobotAPITokensTab', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    resourceMocks.fetch.mockResolvedValue([]);
    resourceMocks.fetchMintableScopes.mockResolvedValue(['repo:read']);
  });

  it('shows an empty token list', async () => {
    render(<RobotAPITokensTab {...props} />);

    expect(
      await screen.findByText(
        'No API tokens have been created for this robot.',
      ),
    ).toBeInTheDocument();
    expect(resourceMocks.fetch).toHaveBeenCalledWith('testorg', 'robot', false);
  });

  it('creates a token and displays its secret once', async () => {
    const user = userEvent.setup();
    resourceMocks.create.mockResolvedValue({token: 'signed-token'});
    render(<RobotAPITokensTab {...props} />);

    await user.click(
      await screen.findByRole('button', {name: 'Create API token'}),
    );
    await user.type(screen.getByRole('textbox'), 'CI token');
    await user.click(
      screen.getByRole('checkbox', {name: 'View all visible repositories'}),
    );
    await user.click(screen.getByRole('button', {name: 'Create'}));

    await waitFor(() =>
      expect(resourceMocks.create).toHaveBeenCalledWith(
        'testorg',
        'robot',
        {
          name: 'CI token',
          scope: 'repo:read',
          expiration: 30 * 24 * 60 * 60,
        },
        false,
      ),
    );
    expect(await screen.findByText('signed-token')).toBeInTheDocument();

    await user.click(screen.getByRole('button', {name: 'Done'}));
    expect(screen.queryByText('signed-token')).not.toBeInTheDocument();
  });

  it('shows only scopes the current editor can mint', async () => {
    const user = userEvent.setup();
    resourceMocks.fetchMintableScopes.mockResolvedValue(['repo:read']);
    render(<RobotAPITokensTab {...props} />);

    await user.click(
      await screen.findByRole('button', {name: 'Create API token'}),
    );

    expect(
      await screen.findByRole('checkbox', {
        name: 'View all visible repositories',
      }),
    ).toBeInTheDocument();
    expect(
      screen.queryByRole('checkbox', {name: 'Super User Access'}),
    ).not.toBeInTheDocument();
  });

  it('disables creation when permitted scopes cannot be loaded', async () => {
    const user = userEvent.setup();
    resourceMocks.fetchMintableScopes.mockRejectedValue(new Error('Failed'));
    render(<RobotAPITokensTab {...props} />);

    await user.click(
      await screen.findByRole('button', {name: 'Create API token'}),
    );

    expect(
      await screen.findByText('Unable to load scopes you can grant'),
    ).toBeInTheDocument();
    expect(screen.getByRole('button', {name: 'Create'})).toBeDisabled();
  });

  it('reports a failed token revocation', async () => {
    const user = userEvent.setup();
    resourceMocks.fetch.mockResolvedValue([
      {
        uuid: 'token-uuid',
        name: 'CI token',
        scope: 'repo:read',
        expires_at: '2026-10-01T00:00:00Z',
      },
    ]);
    resourceMocks.revoke.mockRejectedValue(new Error('Failed'));
    render(<RobotAPITokensTab {...props} />);

    await user.click(await screen.findByRole('button', {name: 'Revoke'}));

    expect(
      await screen.findByText(
        'Unable to revoke robot API token; it remains active',
      ),
    ).toBeInTheDocument();
  });

  it('lists and revokes an existing token', async () => {
    const user = userEvent.setup();
    resourceMocks.fetch.mockResolvedValue([
      {
        uuid: 'token-uuid',
        name: 'CI token',
        scope: 'repo:read',
        expires_at: '2026-10-01T00:00:00Z',
        created_by: 'devtable',
      },
    ]);
    resourceMocks.revoke.mockResolvedValue(undefined);
    render(<RobotAPITokensTab {...props} />);

    expect(await screen.findByText('CI token')).toBeInTheDocument();
    expect(screen.getByText(/created by devtable/)).toBeInTheDocument();
    await user.click(screen.getByRole('button', {name: 'Revoke'}));

    await waitFor(() =>
      expect(resourceMocks.revoke).toHaveBeenCalledWith(
        'testorg',
        'robot',
        'token-uuid',
        false,
      ),
    );
  });
});
