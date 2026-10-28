import {render, screen, waitFor} from 'src/test-utils';
import ImmutabilityPolicies from './ImmutabilityPolicies';
import {fetchProxyCacheConfig} from 'src/resources/ProxyCacheResource';

const mockUseQuayConfig = vi.hoisted(() => vi.fn());

vi.mock('src/hooks/UseQuayConfig', () => ({
  useQuayConfig: mockUseQuayConfig,
}));

vi.mock('src/resources/ProxyCacheResource', () => ({
  fetchProxyCacheConfig: vi.fn(),
  validateProxyCacheConfig: vi.fn(),
  createProxyCacheConfig: vi.fn(),
  deleteProxyCacheConfig: vi.fn(),
}));

vi.mock('src/hooks/UseOrgMirrorExists', () => ({
  useOrgMirrorExists: () => ({
    isOrgMirrored: false,
    isLoading: false,
    isError: false,
  }),
}));

vi.mock('src/hooks/UseNamespaceImmutabilityPolicies', () => ({
  useNamespaceImmutabilityPolicies: () => ({
    error: null,
    isSuccess: true,
    isLoading: false,
    nsPolicies: [],
    dataUpdatedAt: 0,
  }),
  useCreateNamespaceImmutabilityPolicy: () => ({createPolicy: vi.fn()}),
  useUpdateNamespaceImmutabilityPolicy: () => ({updatePolicy: vi.fn()}),
  useDeleteNamespaceImmutabilityPolicy: () => ({deletePolicy: vi.fn()}),
}));

function setProxyCacheFeature(enabled: boolean) {
  mockUseQuayConfig.mockReturnValue({features: {PROXY_CACHE: enabled}});
}

describe('ImmutabilityPolicies proxy cache guard', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('enables Add Policy without a lookup when PROXY_CACHE is disabled', () => {
    setProxyCacheFeature(false);
    render(<ImmutabilityPolicies org="myorg" />);

    expect(screen.getByTestId('add-immutability-policy-btn')).toBeEnabled();
    expect(
      screen.queryByTestId('proxy-cache-error-alert'),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByTestId('proxy-cache-conflict-alert'),
    ).not.toBeInTheDocument();
    expect(fetchProxyCacheConfig).not.toHaveBeenCalled();
  });

  it('disables Add Policy when the proxy cache lookup fails', async () => {
    setProxyCacheFeature(true);
    vi.mocked(fetchProxyCacheConfig).mockRejectedValue(
      new Error('Request failed with status code 500'),
    );
    render(<ImmutabilityPolicies org="myorg" />);

    expect(
      await screen.findByTestId('proxy-cache-error-alert'),
    ).toBeInTheDocument();
    expect(screen.getByTestId('add-immutability-policy-btn')).toBeDisabled();
  });

  it('disables Add Policy when a proxy cache is configured', async () => {
    setProxyCacheFeature(true);
    vi.mocked(fetchProxyCacheConfig).mockResolvedValue({
      upstream_registry: 'docker.io',
      expiration_s: 86400,
    });
    render(<ImmutabilityPolicies org="myorg" />);

    expect(
      await screen.findByTestId('proxy-cache-conflict-alert'),
    ).toBeInTheDocument();
    await waitFor(() =>
      expect(screen.getByTestId('add-immutability-policy-btn')).toBeDisabled(),
    );
  });
});
