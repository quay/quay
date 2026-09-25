import {render, screen} from 'src/test-utils';
import {RobotFederationModal} from './RobotFederationModal';

const resourceMocks = vi.hoisted(() => ({
  fetchMintableScopes: vi.fn(),
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

vi.mock('src/hooks/useRobotFederation', () => ({
  useRobotFederation: () => ({
    robotFederationConfig: resourceMocks.federationConfig,
    loading: false,
    fetchError: null,
    setRobotFederationConfig: vi.fn(),
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
    resourceMocks.federationConfig = [
      {
        issuer: 'https://issuer.example.com',
        subject: 'robot-subject',
        api_scopes: 'super:user',
      },
    ];
    resourceMocks.fetchMintableScopes.mockResolvedValue(['repo:read']);
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
