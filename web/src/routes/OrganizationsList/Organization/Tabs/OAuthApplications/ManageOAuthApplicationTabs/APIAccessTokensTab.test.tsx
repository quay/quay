import React from 'react';
import {render, screen, userEvent, waitFor, within} from 'src/test-utils';
import APIAccessTokensTab from './APIAccessTokensTab';
import {useCurrentUser} from 'src/hooks/UseCurrentUser';
import {
  useAssignOAuthApplicationTokenToUser,
  useCreateOAuthApplicationToken,
  useFetchOAuthApplicationTokens,
  useRevokeOAuthApplicationToken,
} from 'src/hooks/UseOAuthApplications';
import {useQuayConfig} from 'src/hooks/UseQuayConfig';
import type {
  IOAuthApplication,
  IOAuthApplicationToken,
} from 'src/resources/OAuthApplicationTypes';
import type {IUserResource} from 'src/resources/UserResource';

const hookMocks = vi.hoisted(() => ({
  assignToken: vi.fn(),
  createToken: vi.fn(),
  revokeToken: vi.fn(),
  assigningToken: false,
  creatingToken: false,
  revokingToken: false,
}));

vi.mock('src/components/EntitySearch', () => ({
  default: ({
    onSelect,
    value,
  }: {
    onSelect: (entity: {name: string}) => void;
    value?: string;
  }) => (
    <button
      type="button"
      data-testid="mock-entity-search"
      onClick={() => onSelect({name: 'alice'})}
    >
      {value ? `Selected ${value}` : 'Select alice'}
    </button>
  ),
}));

vi.mock('src/hooks/UseCurrentUser', () => ({
  useCurrentUser: vi.fn(),
}));

vi.mock('src/hooks/UseOAuthApplications', () => ({
  useFetchOAuthApplicationTokens: vi.fn(),
  useCreateOAuthApplicationToken: vi.fn(),
  useAssignOAuthApplicationTokenToUser: vi.fn(),
  useRevokeOAuthApplicationToken: vi.fn(),
}));

vi.mock('src/hooks/UseQuayConfig', () => ({
  useQuayConfig: vi.fn(),
}));

const application: IOAuthApplication = {
  application_uri: 'https://example.com',
  avatar_email: '',
  client_id: 'client1',
  client_secret: 'secret',
  description: 'Test app',
  name: 'test-app',
  redirect_uri: 'https://example.com/callback',
};

const defaultUser: IUserResource = {
  anonymous: false,
  username: 'admin',
  avatar: {name: 'admin', hash: '', color: '', kind: 'user'},
  can_create_repo: true,
  is_me: true,
  verified: true,
  email: 'admin@example.com',
  logins: [
    {
      service: 'quay',
      service_identifier: 'admin',
      metadata: {service_username: 'admin'},
    },
  ],
  invoice_email: false,
  invoice_email_address: '',
  preferred_namespace: false,
  tag_expiration_s: 0,
  prompts: [],
  super_user: false,
  company: '',
  family_name: '',
  given_name: '',
  location: '',
  is_free_account: false,
  has_password_set: true,
  organizations: [],
};

function buildUser(overrides: Partial<IUserResource> = {}): IUserResource {
  return {...defaultUser, ...overrides};
}

function buildToken(
  overrides: Partial<IOAuthApplicationToken> = {},
): IOAuthApplicationToken {
  return {
    uuid: 'token1',
    name: 'Jenkins',
    scope: 'repo:read',
    expires_at: null,
    created: null,
    created_by: null,
    last_accessed: null,
    ...overrides,
  };
}

const createdToken = buildToken({
  uuid: 'generated-token',
  name: 'Generated token',
  expires_at: '2026-01-01T00:00:00Z',
  created: '2025-01-01T00:00:00Z',
  created_by: 'admin',
  token: 'secret-token',
});

const listedToken = buildToken({created_by: 'admin'});

function mockDefaultHooks(tokens: IOAuthApplicationToken[] = []): void {
  vi.mocked(useCurrentUser).mockReturnValue({
    user: buildUser(),
    loading: false,
    error: null,
    isSuperUser: false,
  });
  vi.mocked(useQuayConfig).mockReturnValue({
    features: {ASSIGN_OAUTH_TOKEN: true},
    config: {LOCAL_OAUTH_HANDLER: '/oauth/localapp'},
  });
  vi.mocked(useFetchOAuthApplicationTokens).mockReturnValue({
    tokens,
    errorRefreshingOAuthApplicationTokens: false,
  });
  vi.mocked(useCreateOAuthApplicationToken).mockImplementation(
    (_org, _clientId, onSuccess, onError) => ({
      createOAuthApplicationTokenMutation: vi.fn(),
      createOAuthApplicationTokenMutationAsync: async (params) => {
        try {
          const token = await hookMocks.createToken(params);
          onSuccess?.(token);
          return token;
        } catch (error) {
          onError?.(error);
          throw error;
        }
      },
      creatingOAuthApplicationToken: hookMocks.creatingToken,
      resetCreateOAuthApplicationToken: vi.fn(),
    }),
  );
  vi.mocked(useAssignOAuthApplicationTokenToUser).mockImplementation(
    (_clientId, onSuccess, onError) => ({
      assignOAuthApplicationTokenToUserMutation: vi.fn(),
      assignOAuthApplicationTokenToUserMutationAsync: async (params) => {
        try {
          const response = await hookMocks.assignToken(params);
          onSuccess?.(response);
          return response;
        } catch (error) {
          onError?.(error);
          throw error;
        }
      },
      assigningOAuthApplicationTokenToUser: hookMocks.assigningToken,
      resetAssignOAuthApplicationTokenToUser: vi.fn(),
    }),
  );
  vi.mocked(useRevokeOAuthApplicationToken).mockImplementation(
    (_org, _clientId, onSuccess, onError) => ({
      revokeOAuthApplicationTokenMutation: vi.fn(),
      revokeOAuthApplicationTokenMutationAsync: async (tokenUuid) => {
        try {
          const response = await hookMocks.revokeToken(tokenUuid);
          onSuccess?.();
          return response;
        } catch (error) {
          onError?.(error);
          throw error;
        }
      },
      revokingOAuthApplicationToken: hookMocks.revokingToken,
      resetRevokeOAuthApplicationToken: vi.fn(),
    }),
  );
}

describe('APIAccessTokensTab', () => {
  beforeEach(() => {
    vi.resetAllMocks();
    hookMocks.assigningToken = false;
    hookMocks.creatingToken = false;
    hookMocks.revokingToken = false;
    hookMocks.createToken.mockResolvedValue(createdToken);
    hookMocks.assignToken.mockResolvedValue({
      message: 'Token assigned successfully',
    });
    hookMocks.revokeToken.mockResolvedValue(undefined);
  });

  it('wraps the empty token state in a PageSection without a body wrapper', () => {
    mockDefaultHooks();
    const {container} = render(
      <APIAccessTokensTab application={application} orgName="myorg" />,
    );

    const pageSection = container.querySelector('.pf-v6-c-page__main-section');
    expect(pageSection).toContainElement(
      screen.getByTestId('generate-new-api-token-button'),
    );
    expect(pageSection).toContainElement(
      screen.getByText('No API access tokens'),
    );
    expect(pageSection?.querySelector('.pf-v6-c-page__main-body')).toBeNull();
  });

  it.each([
    {
      accessMode: 'global read-only superuser mode',
      configureReadOnlyAccess: () => {
        vi.mocked(useCurrentUser).mockReturnValue({
          user: buildUser({
            username: 'auditor',
            global_readonly_super_user: true,
          }),
          loading: false,
          error: null,
          isSuperUser: true,
        });
      },
    },
    {
      accessMode: 'registry read-only mode',
      configureReadOnlyAccess: () => {
        vi.mocked(useQuayConfig).mockReturnValue({
          features: {ASSIGN_OAUTH_TOKEN: true},
          config: {LOCAL_OAUTH_HANDLER: '/oauth/localapp'},
          registry_state: 'readonly',
        });
      },
    },
  ])(
    'preserves inventory but hides mutation controls in $accessMode',
    ({configureReadOnlyAccess}) => {
      mockDefaultHooks([listedToken]);
      configureReadOnlyAccess();

      render(<APIAccessTokensTab application={application} orgName="myorg" />);

      expect(screen.getByTestId('api-access-tokens-table')).toBeVisible();
      expect(screen.getByText('Jenkins')).toBeVisible();
      expect(
        screen.queryByTestId('generate-new-api-token-button'),
      ).not.toBeInTheDocument();
      expect(
        screen.queryByTestId('api-token-actions-token1'),
      ).not.toBeInTheDocument();
      expect(screen.queryByText('Actions')).not.toBeInTheDocument();
    },
  );

  it('uses the fixed expiration dropdown options when generating a token', async () => {
    const user = userEvent.setup();
    mockDefaultHooks();
    render(<APIAccessTokensTab application={application} orgName="myorg" />);

    await user.click(screen.getByTestId('generate-new-api-token-button'));
    const expirationSelect = screen.getByTestId('api-token-expiration-select');
    expect(expirationSelect).toHaveValue('10-years');
    for (const option of [
      '7 days',
      '30 days',
      '90 days',
      '1 year',
      '10 years',
    ]) {
      expect(
        within(expirationSelect).getByRole('option', {name: option}),
      ).toBeInTheDocument();
    }

    await user.selectOptions(expirationSelect, '7-days');
    await user.type(screen.getByTestId('api-token-name-input'), 'Jenkins');
    await user.click(screen.getByTestId('api-token-scope-org:admin'));
    await user.click(screen.getByTestId('generate-api-token-submit'));

    expect(hookMocks.createToken).not.toHaveBeenCalled();
    expect(await screen.findByText('test-app')).toBeVisible();
    expect(
      screen.getByText(
        'This scope grants permissions which are potentially dangerous. Be careful when authorizing it!',
      ),
    ).toBeVisible();

    await user.click(
      screen.getByRole('button', {name: 'Authorize Application'}),
    );

    await waitFor(() =>
      expect(hookMocks.createToken).toHaveBeenCalledWith({
        name: 'Jenkins',
        scope: 'org:admin',
        expiration: 7 * 24 * 60 * 60,
      }),
    );
    expect(await screen.findByTestId('token-display-modal')).toBeVisible();
    expect(screen.getByDisplayValue('secret-token')).toBeVisible();
    expect(screen.getByRole('button', {name: 'Show content'})).toBeVisible();
  });

  it('keeps the one-time secret visible when the token-list refresh fails', async () => {
    const user = userEvent.setup();
    mockDefaultHooks();
    const {rerender} = render(
      <APIAccessTokensTab application={application} orgName="myorg" />,
    );

    await user.click(screen.getByTestId('generate-new-api-token-button'));
    await user.type(screen.getByTestId('api-token-name-input'), 'Jenkins');
    await user.click(screen.getByTestId('api-token-scope-repo:read'));
    await user.click(screen.getByTestId('generate-api-token-submit'));
    await user.click(
      screen.getByRole('button', {name: 'Authorize Application'}),
    );
    expect(await screen.findByDisplayValue('secret-token')).toBeVisible();

    vi.mocked(useFetchOAuthApplicationTokens).mockReturnValue({
      tokens: [],
      errorRefreshingOAuthApplicationTokens: true,
    });
    rerender(<APIAccessTokensTab application={application} orgName="myorg" />);

    expect(screen.getByDisplayValue('secret-token')).toBeVisible();
    expect(screen.getByTestId('api-access-tokens-refresh-error')).toBeVisible();
    expect(screen.queryByText('Unable to load API access tokens')).toBeNull();
  });

  it('locks authorization controls while a token request is pending', async () => {
    const user = userEvent.setup();
    mockDefaultHooks();
    const {rerender} = render(
      <APIAccessTokensTab application={application} orgName="myorg" />,
    );

    await user.click(screen.getByTestId('generate-new-api-token-button'));
    await user.type(screen.getByTestId('api-token-name-input'), 'Jenkins');
    await user.click(screen.getByTestId('api-token-scope-repo:read'));
    await user.click(screen.getByTestId('generate-api-token-submit'));

    hookMocks.creatingToken = true;
    rerender(<APIAccessTokensTab application={application} orgName="myorg" />);

    expect(
      screen.getByRole('button', {name: /Authorize Application/}),
    ).toBeDisabled();
    expect(screen.getByRole('button', {name: 'Cancel'})).toBeDisabled();
    expect(screen.queryByRole('button', {name: 'Close'})).toBeNull();
  });

  it('submits only one create request when authorization is double-clicked', async () => {
    const user = userEvent.setup();
    let resolveCreateToken!: (token: typeof createdToken) => void;
    hookMocks.createToken.mockImplementation(
      () =>
        new Promise((resolve) => {
          resolveCreateToken = resolve;
        }),
    );
    mockDefaultHooks();
    render(<APIAccessTokensTab application={application} orgName="myorg" />);

    await user.click(screen.getByTestId('generate-new-api-token-button'));
    await user.type(screen.getByTestId('api-token-name-input'), 'Jenkins');
    await user.click(screen.getByTestId('api-token-scope-repo:read'));
    await user.click(screen.getByTestId('generate-api-token-submit'));
    await user.dblClick(
      screen.getByRole('button', {name: 'Authorize Application'}),
    );

    expect(hookMocks.createToken).toHaveBeenCalledTimes(1);

    resolveCreateToken(createdToken);
    expect(await screen.findByTestId('token-display-modal')).toBeVisible();
  });

  it('clears generate modal state when canceling after an error', async () => {
    const user = userEvent.setup();
    hookMocks.createToken.mockRejectedValueOnce(new Error('Create failed'));
    mockDefaultHooks();
    render(<APIAccessTokensTab application={application} orgName="myorg" />);

    await user.click(screen.getByTestId('generate-new-api-token-button'));
    const expirationSelect = screen.getByTestId('api-token-expiration-select');
    await user.selectOptions(expirationSelect, '7-days');
    await user.type(screen.getByTestId('api-token-name-input'), 'Jenkins');
    await user.click(screen.getByTestId('api-token-scope-repo:read'));
    await user.click(screen.getByTestId('generate-api-token-submit'));
    await user.click(
      await screen.findByRole('button', {name: 'Authorize Application'}),
    );

    expect(await screen.findByTestId('generate-api-token-error')).toBeVisible();

    await user.click(screen.getByRole('button', {name: 'Cancel'}));
    await user.click(screen.getByTestId('generate-new-api-token-button'));

    expect(screen.queryByTestId('generate-api-token-error')).toBeNull();
    expect(screen.getByTestId('api-token-name-input')).toHaveValue('');
    expect(screen.getByTestId('api-token-expiration-select')).toHaveValue(
      '10-years',
    );
    expect(screen.getByTestId('api-token-scope-repo:read')).not.toBeChecked();
  });

  it('hides user assignment when the feature is disabled', async () => {
    const user = userEvent.setup();
    mockDefaultHooks();
    vi.mocked(useQuayConfig).mockReturnValue({
      features: {ASSIGN_OAUTH_TOKEN: false},
      config: {LOCAL_OAUTH_HANDLER: '/oauth/localapp'},
    });
    render(<APIAccessTokensTab application={application} orgName="myorg" />);

    await user.click(screen.getByTestId('generate-new-api-token-button'));

    expect(
      screen.queryByRole('button', {name: 'Assign another user'}),
    ).not.toBeInTheDocument();
    expect(screen.getByTestId('api-token-name-input')).toBeVisible();
  });

  it('assigns an OAuth token request to another user when the feature is enabled', async () => {
    const user = userEvent.setup();
    mockDefaultHooks();
    render(<APIAccessTokensTab application={application} orgName="myorg" />);

    await user.click(screen.getByTestId('generate-new-api-token-button'));
    await user.click(screen.getByTestId('assign-user-button'));
    expect(
      screen.queryByTestId('api-token-name-input'),
    ).not.toBeInTheDocument();
    await user.click(screen.getByTestId('mock-entity-search'));
    expect(screen.getByTestId('mock-entity-search')).toHaveTextContent(
      'Selected alice',
    );
    await user.click(screen.getByTestId('api-token-scope-repo:read'));
    await user.click(screen.getByTestId('generate-api-token-submit'));

    expect(await screen.findByText('Assign Authorization?')).toBeVisible();
    expect(
      screen.getByText(
        'This will prompt user alice to generate a token with the following permissions:',
      ),
    ).toBeVisible();

    await user.click(screen.getByRole('button', {name: 'Assign token'}));

    await waitFor(() =>
      expect(hookMocks.assignToken).toHaveBeenCalledWith({
        username: 'alice',
        scope: 'repo:read',
        redirect_uri: `${window.location.origin}/oauth/localapp`,
      }),
    );
    expect(hookMocks.createToken).not.toHaveBeenCalled();
  });

  it('resets assignment mode when canceling the generate modal', async () => {
    const user = userEvent.setup();
    mockDefaultHooks();
    render(<APIAccessTokensTab application={application} orgName="myorg" />);

    await user.click(screen.getByTestId('generate-new-api-token-button'));
    await user.click(screen.getByTestId('assign-user-button'));
    await user.click(screen.getByTestId('mock-entity-search'));
    expect(screen.getByTestId('mock-entity-search')).toHaveTextContent(
      'Selected alice',
    );

    await user.click(screen.getByRole('button', {name: 'Cancel'}));
    await user.click(screen.getByTestId('generate-new-api-token-button'));

    expect(screen.getByTestId('api-token-name-input')).toHaveValue('');
    expect(screen.getByTestId('assign-user-button')).toBeVisible();
    expect(screen.queryByTestId('mock-entity-search')).not.toBeInTheDocument();

    await user.click(screen.getByTestId('assign-user-button'));

    expect(screen.getByTestId('mock-entity-search')).toHaveTextContent(
      'Select alice',
    );
  });

  it('locks revoke controls while a revoke request is pending', async () => {
    const user = userEvent.setup();
    mockDefaultHooks([buildToken()]);
    const {rerender} = render(
      <APIAccessTokensTab application={application} orgName="myorg" />,
    );

    await user.click(screen.getByTestId('api-token-actions-token1'));
    await user.click(
      within(screen.getByTestId('revoke-api-token-token1')).getByRole(
        'menuitem',
        {name: 'Revoke'},
      ),
    );

    hookMocks.revokingToken = true;
    rerender(<APIAccessTokensTab application={application} orgName="myorg" />);

    expect(screen.getByRole('button', {name: /Revoke token/})).toBeDisabled();
    expect(screen.getByRole('button', {name: 'Cancel'})).toBeDisabled();
    expect(screen.queryByRole('button', {name: 'Close'})).toBeNull();
  });

  it('submits only one revoke request when confirmation is double-clicked', async () => {
    const user = userEvent.setup();
    let resolveRevokeToken!: () => void;
    hookMocks.revokeToken.mockImplementation(
      () =>
        new Promise<void>((resolve) => {
          resolveRevokeToken = resolve;
        }),
    );
    mockDefaultHooks([buildToken()]);
    render(<APIAccessTokensTab application={application} orgName="myorg" />);

    await user.click(screen.getByTestId('api-token-actions-token1'));
    await user.click(
      within(screen.getByTestId('revoke-api-token-token1')).getByRole(
        'menuitem',
        {name: 'Revoke'},
      ),
    );
    await user.dblClick(screen.getByTestId('revoke-api-token-confirm'));

    expect(hookMocks.revokeToken).toHaveBeenCalledTimes(1);

    resolveRevokeToken();
    await waitFor(() =>
      expect(screen.queryByTestId('revoke-api-token-modal')).toBeNull(),
    );
  });

  it('clears revoke errors when canceling the modal', async () => {
    const user = userEvent.setup();
    hookMocks.revokeToken.mockRejectedValueOnce(new Error('Revoke failed'));
    mockDefaultHooks([buildToken()]);
    render(<APIAccessTokensTab application={application} orgName="myorg" />);

    await user.click(screen.getByTestId('api-token-actions-token1'));
    await user.click(
      within(screen.getByTestId('revoke-api-token-token1')).getByRole(
        'menuitem',
        {name: 'Revoke'},
      ),
    );
    await user.click(screen.getByTestId('revoke-api-token-confirm'));

    expect(await screen.findByTestId('revoke-api-token-error')).toBeVisible();

    await user.click(screen.getByRole('button', {name: 'Cancel'}));
    await user.click(screen.getByTestId('api-token-actions-token1'));
    await user.click(
      within(screen.getByTestId('revoke-api-token-token1')).getByRole(
        'menuitem',
        {name: 'Revoke'},
      ),
    );

    expect(await screen.findByTestId('revoke-api-token-modal')).toBeVisible();
    expect(screen.queryByTestId('revoke-api-token-error')).toBeNull();
  });

  it('uses a kebab row action and wraps long scope lists', async () => {
    const user = userEvent.setup();
    mockDefaultHooks([
      buildToken({
        name: null,
        scope: 'org:admin repo:admin repo:create repo:read repo:write',
      }),
    ]);
    render(<APIAccessTokensTab application={application} orgName="myorg" />);

    for (const header of screen.getAllByRole('columnheader')) {
      expect(header).toHaveClass('pf-m-nowrap');
    }
    expect(screen.getByText('Actions')).toHaveClass('pf-v6-u-screen-reader');
    expect(
      screen
        .getByTestId('api-access-tokens-table')
        .querySelector('td[data-label="Name"]'),
    ).toBeEmptyDOMElement();
    expect(screen.getByTestId('api-token-actions-token1')).toHaveAccessibleName(
      'Actions for token1',
    );
    expect(
      screen.getByText('Never', {selector: 'td[data-label="Last Used"]'}),
    ).toBeVisible();
    const scopeSummary = screen.getByTestId('api-token-scopes-summary');
    expect(scopeSummary).toHaveTextContent(
      'org:admin, repo:admin, repo:create, repo:read, repo:write',
    );
    expect(scopeSummary).toHaveStyle({whiteSpace: 'normal'});
    expect(
      screen.queryByTestId('revoke-api-token-token1'),
    ).not.toBeInTheDocument();

    await user.click(screen.getByTestId('api-token-actions-token1'));
    await user.click(
      within(screen.getByTestId('revoke-api-token-token1')).getByRole(
        'menuitem',
        {name: 'Revoke'},
      ),
    );

    expect(await screen.findByTestId('revoke-api-token-modal')).toBeVisible();
    expect(screen.getByText('token1')).toBeVisible();
  });
});
