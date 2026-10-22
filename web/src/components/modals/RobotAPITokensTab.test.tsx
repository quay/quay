import {screen, render, userEvent, waitFor, within} from 'src/test-utils';
import {formatDate, formatRelativeTime} from 'src/libs/utils';
import {IRobotAPIToken} from 'src/resources/RobotsResource';
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
  canManageRobotAPITokens: true,
};

const DAY_MS = 24 * 60 * 60 * 1000;
const inDays = (days: number): string =>
  new Date(Date.now() + days * DAY_MS).toISOString();
const makeToken = (
  overrides: Partial<IRobotAPIToken> & {uuid: string},
): IRobotAPIToken => ({
  name: overrides.uuid,
  scope: 'repo:read',
  expires_at: inDays(30),
  created: inDays(-1),
  created_by: 'devtable',
  last_accessed: null,
  ...overrides,
});

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

  it('keeps the token list read-only without namespace management permission', async () => {
    resourceMocks.fetch.mockResolvedValue([
      makeToken({uuid: 'token-uuid', name: 'Audited token'}),
    ]);
    render(<RobotAPITokensTab {...props} canManageRobotAPITokens={false} />);

    const table = await screen.findByTestId('robot-api-tokens-table');
    expect(within(table).getByText('Audited token')).toBeInTheDocument();
    expect(screen.queryByRole('button', {name: 'Create API token'})).toBeNull();
    expect(screen.queryByRole('button', {name: 'Revoke'})).toBeNull();
    expect(screen.queryByRole('button', {name: 'Revoke selected'})).toBeNull();
    expect(screen.queryByRole('checkbox', {name: 'Select row 0'})).toBeNull();
    expect(
      within(table).queryByRole('columnheader', {name: 'Row select'}),
    ).toBeNull();
    expect(
      within(table).queryByRole('columnheader', {name: 'Actions'}),
    ).toBeNull();
  });

  it('closes the create dialog when namespace management permission is lost', async () => {
    const user = userEvent.setup();
    const {rerender} = render(<RobotAPITokensTab {...props} />);

    await user.click(
      await screen.findByRole('button', {name: 'Create API token'}),
    );
    await user.type(screen.getByRole('textbox'), 'CI token');
    await user.click(
      screen.getByRole('checkbox', {name: 'View all visible repositories'}),
    );
    expect(screen.getByText('Create robot API token')).toBeInTheDocument();

    rerender(<RobotAPITokensTab {...props} canManageRobotAPITokens={false} />);

    await waitFor(() =>
      expect(
        screen.queryByText('Create robot API token'),
      ).not.toBeInTheDocument(),
    );
    expect(resourceMocks.create).not.toHaveBeenCalled();

    rerender(<RobotAPITokensTab {...props} />);

    expect(
      screen.queryByText('Create robot API token'),
    ).not.toBeInTheDocument();
    expect(resourceMocks.create).not.toHaveBeenCalled();
  });

  it('closes the bulk revoke confirmation when namespace management permission is lost', async () => {
    const user = userEvent.setup();
    resourceMocks.fetch.mockResolvedValue([
      makeToken({uuid: 'token-uuid', name: 'Audited token'}),
    ]);
    const {rerender} = render(<RobotAPITokensTab {...props} />);

    await screen.findByText('Audited token');
    await user.click(screen.getByRole('checkbox', {name: 'Select row 0'}));
    await user.click(screen.getByRole('button', {name: 'Revoke selected'}));
    expect(await screen.findByTestId('bulk-delete-modal')).toBeInTheDocument();

    rerender(<RobotAPITokensTab {...props} canManageRobotAPITokens={false} />);

    await waitFor(() =>
      expect(screen.queryByTestId('bulk-delete-modal')).not.toBeInTheDocument(),
    );
    expect(resourceMocks.revoke).not.toHaveBeenCalled();

    rerender(<RobotAPITokensTab {...props} />);

    expect(screen.queryByTestId('bulk-delete-modal')).not.toBeInTheDocument();
    expect(
      screen.queryByRole('button', {name: 'Revoke selected'}),
    ).not.toBeInTheDocument();
    expect(resourceMocks.revoke).not.toHaveBeenCalled();
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

  it('clears creation errors after editing or reopening the form', async () => {
    const user = userEvent.setup();
    resourceMocks.create.mockRejectedValue(new Error('Failed'));
    render(<RobotAPITokensTab {...props} />);

    await user.click(
      await screen.findByRole('button', {name: 'Create API token'}),
    );
    await user.type(screen.getByRole('textbox'), 'CI token');
    await user.click(
      screen.getByRole('checkbox', {name: 'View all visible repositories'}),
    );
    await user.click(screen.getByRole('button', {name: 'Create'}));
    expect(
      await screen.findByText('Unable to create API token'),
    ).toBeInTheDocument();

    await user.type(screen.getByRole('textbox'), ' updated');
    expect(
      screen.queryByText('Unable to create API token'),
    ).not.toBeInTheDocument();

    await user.click(screen.getByRole('button', {name: 'Create'}));
    expect(
      await screen.findByText('Unable to create API token'),
    ).toBeInTheDocument();
    await user.click(screen.getByRole('button', {name: 'Cancel'}));
    await user.click(screen.getByRole('button', {name: 'Create API token'}));
    expect(
      screen.queryByText('Unable to create API token'),
    ).not.toBeInTheDocument();
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

  it('shows revocation progress only for the selected token', async () => {
    const user = userEvent.setup();
    resourceMocks.fetch.mockResolvedValue([
      {
        uuid: 'first-token',
        name: 'First token',
        scope: 'repo:read',
        expires_at: '2026-10-01T00:00:00Z',
      },
      {
        uuid: 'second-token',
        name: 'Second token',
        scope: 'repo:read',
        expires_at: '2026-10-01T00:00:00Z',
      },
    ]);
    let finishRevocation: () => void = () => undefined;
    resourceMocks.revoke.mockReturnValue(
      new Promise<void>((resolve) => {
        finishRevocation = resolve;
      }),
    );
    render(<RobotAPITokensTab {...props} />);

    const revokeButtons = await screen.findAllByRole('button', {
      name: 'Revoke',
    });
    await user.click(revokeButtons[0]);

    await waitFor(() => expect(revokeButtons[0]).toBeDisabled());
    expect(
      revokeButtons[0].querySelector('.pf-v6-c-spinner'),
    ).toBeInTheDocument();
    expect(revokeButtons[1]).toBeDisabled();
    expect(
      revokeButtons[1].querySelector('.pf-v6-c-spinner'),
    ).not.toBeInTheDocument();

    finishRevocation();
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
    expect(screen.getByText('devtable')).toBeInTheDocument();
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

  it('lists tokens in a table with name, scope, expiry, last access and creator columns', async () => {
    resourceMocks.fetch.mockResolvedValue([
      makeToken({uuid: 'token-uuid', name: 'CI token', scope: 'repo:read'}),
    ]);
    render(<RobotAPITokensTab {...props} />);

    const table = await screen.findByTestId('robot-api-tokens-table');
    for (const column of [
      'Token name',
      'Scopes',
      'Expires',
      'Last accessed',
      'Created by',
    ]) {
      expect(
        within(table).getByRole('columnheader', {name: column}),
      ).toBeInTheDocument();
    }
    expect(within(table).getByText('CI token')).toBeInTheDocument();
    expect(within(table).getByText('repo:read')).toBeInTheDocument();
    expect(within(table).getByText('devtable')).toBeInTheDocument();
  });

  it('formats expiry and last access as relative times with the full date in a tooltip', async () => {
    const user = userEvent.setup();
    const expiresAt = inDays(30);
    const lastAccessed = new Date(
      Date.now() - 2 * 60 * 60 * 1000,
    ).toISOString();
    resourceMocks.fetch.mockResolvedValue([
      makeToken({
        uuid: 'token-uuid',
        name: 'CI token',
        expires_at: expiresAt,
        last_accessed: lastAccessed,
      }),
    ]);
    render(<RobotAPITokensTab {...props} />);

    const expiry = await screen.findByText(formatRelativeTime(expiresAt));
    expect(
      screen.getByText(formatRelativeTime(lastAccessed)),
    ).toBeInTheDocument();
    expect(
      screen.queryByText(expiresAt, {exact: false}),
    ).not.toBeInTheDocument();

    await user.hover(expiry);
    expect(await screen.findByRole('tooltip')).toHaveTextContent(
      formatDate(expiresAt),
    );
  });

  it('shows Never for a token that has not been used', async () => {
    resourceMocks.fetch.mockResolvedValue([
      makeToken({uuid: 'token-uuid', name: 'CI token', last_accessed: null}),
    ]);
    render(<RobotAPITokensTab {...props} />);

    expect(await screen.findByText('Never')).toBeInTheDocument();
  });

  it('marks expired tokens', async () => {
    resourceMocks.fetch.mockResolvedValue([
      makeToken({uuid: 'old', name: 'Old token', expires_at: inDays(-3)}),
      makeToken({uuid: 'new', name: 'New token', expires_at: inDays(3)}),
    ]);
    render(<RobotAPITokensTab {...props} />);

    await screen.findByText('Old token');
    expect(screen.getAllByText('Expired')).toHaveLength(1);
  });

  it('filters tokens by name', async () => {
    const user = userEvent.setup();
    resourceMocks.fetch.mockResolvedValue([
      makeToken({uuid: 'alpha', name: 'alpha-token'}),
      makeToken({uuid: 'beta', name: 'beta-token'}),
    ]);
    render(<RobotAPITokensTab {...props} />);

    await screen.findByText('alpha-token');
    await user.type(screen.getByTestId('robot-api-token-search'), 'BETA');

    expect(screen.queryByText('alpha-token')).not.toBeInTheDocument();
    expect(screen.getByText('beta-token')).toBeInTheDocument();
  });

  it('explains when no token matches the search', async () => {
    const user = userEvent.setup();
    resourceMocks.fetch.mockResolvedValue([
      makeToken({uuid: 'alpha', name: 'alpha-token'}),
    ]);
    render(<RobotAPITokensTab {...props} />);

    await screen.findByText('alpha-token');
    await user.type(screen.getByTestId('robot-api-token-search'), 'zzz');

    expect(
      screen.getByText('No API tokens match the search.'),
    ).toBeInTheDocument();
    expect(
      screen.queryByText('No API tokens have been created for this robot.'),
    ).not.toBeInTheDocument();
  });

  it('paginates tokens ten per page', async () => {
    const user = userEvent.setup();
    resourceMocks.fetch.mockResolvedValue(
      Array.from({length: 12}, (_, index) =>
        makeToken({
          uuid: `token-${index + 1}`,
          name: `Token ${String(index + 1).padStart(2, '0')}`,
        }),
      ),
    );
    render(<RobotAPITokensTab {...props} />);

    expect(await screen.findByText('Token 10')).toBeInTheDocument();
    expect(screen.queryByText('Token 11')).not.toBeInTheDocument();

    await user.click(
      screen.getAllByRole('button', {name: 'Go to next page'})[0],
    );

    expect(await screen.findByText('Token 11')).toBeInTheDocument();
    expect(screen.queryByText('Token 10')).not.toBeInTheDocument();
  });

  it('revokes the selected tokens after confirmation', async () => {
    const user = userEvent.setup();
    resourceMocks.fetch.mockResolvedValue([
      makeToken({uuid: 'first-token', name: 'First token'}),
      makeToken({uuid: 'second-token', name: 'Second token'}),
      makeToken({uuid: 'third-token', name: 'Third token'}),
    ]);
    resourceMocks.revoke.mockResolvedValue(undefined);
    render(<RobotAPITokensTab {...props} />);

    await screen.findByText('First token');
    expect(
      screen.queryByRole('button', {name: 'Revoke selected'}),
    ).not.toBeInTheDocument();
    await user.click(screen.getByRole('checkbox', {name: 'Select row 0'}));
    await user.click(screen.getByRole('checkbox', {name: 'Select row 1'}));
    await user.click(screen.getByRole('button', {name: 'Revoke selected'}));

    const modal = await screen.findByTestId('bulk-delete-modal');
    expect(
      within(modal).getByRole('heading', {
        name: /Revoke 2 robot API tokens\?/,
      }),
    ).toBeInTheDocument();
    expect(
      within(modal).getByText(
        'Only the selected tokens are revoked. A revoked token stops working at once and cannot be restored.',
      ),
    ).toBeInTheDocument();
    expect(
      within(modal).getByText(/Confirm revocation by typing/),
    ).toBeInTheDocument();
    expect(
      within(modal).queryByText(/Permanently delete/),
    ).not.toBeInTheDocument();
    expect(within(modal).getByText('First token')).toBeInTheDocument();
    expect(within(modal).getByText('Second token')).toBeInTheDocument();
    expect(within(modal).queryByText('Third token')).not.toBeInTheDocument();
    await user.type(
      within(modal).getByTestId('delete-confirmation-input'),
      'confirm',
    );
    const confirmButton = within(modal).getByTestId('bulk-delete-confirm-btn');
    expect(confirmButton).toHaveTextContent('Revoke');
    await user.click(confirmButton);

    await waitFor(() => expect(resourceMocks.revoke).toHaveBeenCalledTimes(2));
    expect(resourceMocks.revoke).toHaveBeenCalledWith(
      'testorg',
      'robot',
      'first-token',
      false,
    );
    expect(resourceMocks.revoke).toHaveBeenCalledWith(
      'testorg',
      'robot',
      'second-token',
      false,
    );
    await waitFor(() =>
      expect(screen.queryByTestId('bulk-delete-modal')).not.toBeInTheDocument(),
    );
  });

  it('names a single selected token in the revoke confirmation', async () => {
    const user = userEvent.setup();
    resourceMocks.fetch.mockResolvedValue([
      makeToken({uuid: 'only-token', name: 'Only token'}),
    ]);
    render(<RobotAPITokensTab {...props} />);

    await screen.findByText('Only token');
    await user.click(screen.getByRole('checkbox', {name: 'Select row 0'}));
    await user.click(screen.getByRole('button', {name: 'Revoke selected'}));

    const modal = await screen.findByTestId('bulk-delete-modal');
    expect(
      within(modal).getByRole('heading', {name: /Revoke 1 robot API token\?/}),
    ).toBeInTheDocument();
  });

  it('reports which tokens failed to revoke in bulk', async () => {
    const user = userEvent.setup();
    resourceMocks.fetch.mockResolvedValue([
      makeToken({uuid: 'first-token', name: 'First token'}),
      makeToken({uuid: 'second-token', name: 'Second token'}),
    ]);
    resourceMocks.revoke.mockImplementation((_ns, _robot, uuid: string) =>
      uuid === 'second-token'
        ? Promise.reject(new Error('Failed'))
        : Promise.resolve(),
    );
    render(<RobotAPITokensTab {...props} />);

    await screen.findByText('First token');
    await user.click(screen.getByRole('checkbox', {name: 'Select row 0'}));
    await user.click(screen.getByRole('checkbox', {name: 'Select row 1'}));
    await user.click(screen.getByRole('button', {name: 'Revoke selected'}));
    const modal = await screen.findByTestId('bulk-delete-modal');
    await user.type(
      within(modal).getByTestId('delete-confirmation-input'),
      'confirm',
    );
    await user.click(within(modal).getByTestId('bulk-delete-confirm-btn'));

    expect(
      await screen.findByText(
        'Unable to revoke 1 of 2 selected tokens; they remain active: Second token',
      ),
    ).toBeInTheDocument();
  });

  it('truncates long token names and shows the full name on hover', async () => {
    const user = userEvent.setup();
    const longName = 'ci-' + 'x'.repeat(120) + '-token';
    resourceMocks.fetch.mockResolvedValue([
      makeToken({uuid: 'long-token', name: longName}),
    ]);
    render(<RobotAPITokensTab {...props} />);

    const name = await screen.findByText(longName);
    expect(name.closest('td')).toHaveClass('pf-m-truncate');

    await user.hover(name);
    expect(await screen.findByRole('tooltip')).toHaveTextContent(longName);
  });

  it('falls back to the last page when the current page empties', async () => {
    const user = userEvent.setup();
    const tokens = Array.from({length: 11}, (_, index) =>
      makeToken({
        uuid: `token-${index + 1}`,
        name: `Token ${String(index + 1).padStart(2, '0')}`,
      }),
    );
    resourceMocks.fetch.mockResolvedValue(tokens);
    resourceMocks.revoke.mockImplementation(() => {
      resourceMocks.fetch.mockResolvedValue(tokens.slice(0, 10));
      return Promise.resolve();
    });
    render(<RobotAPITokensTab {...props} />);

    await screen.findByText('Token 01');
    await user.click(
      screen.getAllByRole('button', {name: 'Go to next page'})[0],
    );
    await user.click(await screen.findByRole('button', {name: 'Revoke'}));

    expect(await screen.findByText('Token 10')).toBeInTheDocument();
    expect(screen.queryByText('Token 11')).not.toBeInTheDocument();
    expect(
      screen.queryByText('No API tokens match the search.'),
    ).not.toBeInTheDocument();
  });
});
