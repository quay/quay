import {render, screen} from 'src/test-utils';
import ProxyCacheConfig from './ProxyCacheConfig';

const mockUseSuperuserPermissions = vi.hoisted(() =>
  vi.fn(() => ({isReadOnlySuperUser: false})),
);

const mockUseFetchProxyCacheConfig = vi.hoisted(() =>
  vi.fn(() => ({
    fetchedProxyCacheConfig: {
      upstream_registry: 'docker.io',
      expiration_s: 86400,
    },
    isLoading: false,
    isError: false,
  })),
);

vi.mock('src/hooks/UseSuperuserPermissions', () => ({
  useSuperuserPermissions: mockUseSuperuserPermissions,
}));

vi.mock('src/hooks/UseProxyCache', () => ({
  useFetchProxyCacheConfig: mockUseFetchProxyCacheConfig,
  useCreateProxyCacheConfig: () => ({
    createProxyCacheConfig: vi.fn(),
    isCreating: false,
    errorCreating: null,
    successCreating: false,
  }),
  useDeleteProxyCacheConfig: () => ({
    deleteProxyCacheConfig: vi.fn(),
    isDeleting: false,
    errorDeleting: null,
    successDeleting: false,
  }),
}));

vi.mock('src/hooks/UseQuayConfig', () => ({
  useQuayConfig: () => ({
    features: {PROXY_CACHE: true},
    config: {},
  }),
}));

describe('ProxyCacheConfig', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockUseSuperuserPermissions.mockReturnValue({isReadOnlySuperUser: false});
  });

  it('enables save button for non-readonly user', () => {
    render(<ProxyCacheConfig organizationName="myorg" isUser={false} />);
    const saveBtn = screen.getByText('Save');
    expect(saveBtn.closest('button')).not.toBeDisabled();
  });

  it('disables save button for readonly superuser', () => {
    mockUseSuperuserPermissions.mockReturnValue({isReadOnlySuperUser: true});
    render(<ProxyCacheConfig organizationName="myorg" isUser={false} />);
    const saveBtn = screen.getByText('Save');
    expect(saveBtn.closest('button')).toBeDisabled();
  });

  it('disables delete button for readonly superuser', () => {
    mockUseSuperuserPermissions.mockReturnValue({isReadOnlySuperUser: true});
    render(<ProxyCacheConfig organizationName="myorg" isUser={false} />);
    const deleteBtn = screen.getByText('Delete');
    expect(deleteBtn.closest('button')).toBeDisabled();
  });
});
