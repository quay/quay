import {render, screen, userEvent, waitFor} from 'src/test-utils';
import {RobotFederationModal} from './RobotFederationModal';

const configMocks = vi.hoisted(() => ({
  apiTokenExchangeEnabled: true,
}));

const resourceMocks = vi.hoisted(() => ({
  fetchMintableScopes: vi.fn(),
  setFederationConfig: vi.fn(),
  loading: false,
  fetchError: null,
  federationConfig: [
    {
      issuer: 'https://issuer.example.com',
      subject: 'robot-subject',
      api_scopes: 'super:user',
    },
  ],
}));

vi.mock('src/resources/RobotsResource', async () => {
  const actual = await vi.importActual('src/resources/RobotsResource');
  return {
    ...actual,
    fetchRobotMintableScopes: resourceMocks.fetchMintableScopes,
  };
});

vi.mock('src/hooks/UseQuayConfig', () => ({
  useQuayConfig: () => ({
    features: {
      ROBOT_API_TOKEN_EXCHANGE: configMocks.apiTokenExchangeEnabled,
    },
  }),
}));

vi.mock('src/hooks/useRobotFederation', () => ({
  useRobotFederation: () => ({
    robotFederationConfig: resourceMocks.federationConfig,
    loading: resourceMocks.loading,
    fetchError: resourceMocks.fetchError,
    setRobotFederationConfig: resourceMocks.setFederationConfig,
  }),
}));

const props = {
  robotAccount: {
    name: 'testorg+robot',
    created: '',
    last_accessed: '',
    description: '',
  },
  namespace: 'testorg',
  isUser: false,
  isModalOpen: true,
  setIsModalOpen: vi.fn(),
};

describe('RobotFederationModal', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    configMocks.apiTokenExchangeEnabled = true;
    resourceMocks.federationConfig = [
      {
        issuer: 'https://issuer.example.com',
        subject: 'robot-subject',
        api_scopes: 'super:user',
      },
    ];
    resourceMocks.loading = false;
    resourceMocks.fetchError = null;
    resourceMocks.fetchMintableScopes.mockResolvedValue(['repo:read']);
  });

  it('adds, edits, and saves a federation binding', async () => {
    const user = userEvent.setup();
    resourceMocks.federationConfig = [];

    render(<RobotFederationModal {...props} />);

    await user.click(
      await screen.findByRole('button', {name: 'Add federation entry'}),
    );
    const [issuerInput, subjectInput, audienceInput] =
      screen.getAllByRole('textbox');
    await user.type(issuerInput, 'https://issuer.example.com');
    await user.type(subjectInput, 'robot-subject');
    await user.clear(audienceInput);
    await user.type(audienceInput, 'quay-ui, quay-cli');
    await user.click(
      screen.getByRole('checkbox', {name: 'View all visible repositories'}),
    );
    await user.click(screen.getByRole('button', {name: 'Save'}));

    await waitFor(() =>
      expect(resourceMocks.setFederationConfig).toHaveBeenCalledWith({
        namespace: 'testorg',
        robotName: 'testorg+robot',
        config: [
          {
            issuer: 'https://issuer.example.com',
            subject: 'robot-subject',
            audiences: ['quay-ui', 'quay-cli'],
            api_scopes: 'repo:read',
          },
        ],
      }),
    );
  });

  it('removes a federation binding before saving', async () => {
    const user = userEvent.setup();
    resourceMocks.fetchMintableScopes.mockResolvedValue(['super:user']);

    render(<RobotFederationModal {...props} />);

    await user.click(
      await screen.findByRole('button', {name: 'Remove federation entry'}),
    );
    await user.click(screen.getByRole('button', {name: 'Save'}));

    expect(resourceMocks.setFederationConfig).toHaveBeenCalledWith({
      namespace: 'testorg',
      robotName: 'testorg+robot',
      config: [],
    });
  });

  it('closes without saving', async () => {
    const user = userEvent.setup();

    render(<RobotFederationModal {...props} />);

    await user.click(await screen.findByText('Close'));
    expect(props.setIsModalOpen).toHaveBeenCalledWith(false);
    expect(resourceMocks.setFederationConfig).not.toHaveBeenCalled();
  });

  it('locks a legacy federation binding with scopes the editor cannot mint', async () => {
    render(<RobotFederationModal {...props} />);

    expect(
      await screen.findByText(
        /One or more configured scopes are no longer available to your account/,
      ),
    ).toBeInTheDocument();
    expect(screen.getByRole('button', {name: 'Save'})).toBeDisabled();
    expect(resourceMocks.fetchMintableScopes).toHaveBeenCalledWith(
      'testorg',
      'testorg+robot',
      false,
    );
  });

  it('uses the user mintable-scopes endpoint for personal robots', async () => {
    render(<RobotFederationModal {...props} isUser />);

    await screen.findByRole('button', {name: 'Save'});
    expect(resourceMocks.fetchMintableScopes).toHaveBeenCalledWith(
      'testorg',
      'testorg+robot',
      true,
    );
  });

  it('disables saving when scope discovery fails', async () => {
    resourceMocks.fetchMintableScopes.mockRejectedValue(new Error('Failed'));

    render(<RobotFederationModal {...props} />);

    expect(
      await screen.findByText('Unable to load scopes you can grant.'),
    ).toBeInTheDocument();
    expect(screen.getByRole('button', {name: 'Save'})).toBeDisabled();
  });

  it('hides scope controls and skips scope discovery when exchange is disabled', async () => {
    configMocks.apiTokenExchangeEnabled = false;

    render(<RobotFederationModal {...props} />);

    expect(await screen.findByRole('button', {name: 'Save'})).toBeEnabled();
    expect(
      screen.queryByText('Management API and registry scopes'),
    ).not.toBeInTheDocument();
    expect(resourceMocks.fetchMintableScopes).not.toHaveBeenCalled();
  });

  it('treats comma-separated scopes as individual scopes', async () => {
    resourceMocks.federationConfig = [
      {
        issuer: 'https://issuer.example.com',
        subject: 'robot-subject',
        api_scopes: 'repo:read,repo:write',
      },
    ];
    resourceMocks.fetchMintableScopes.mockResolvedValue([
      'repo:read',
      'repo:write',
    ]);

    render(<RobotFederationModal {...props} />);

    expect(await screen.findByRole('button', {name: 'Save'})).toBeEnabled();
    expect(
      screen.queryByText(
        /One or more configured scopes are no longer available to your account/,
      ),
    ).not.toBeInTheDocument();
  });
});
