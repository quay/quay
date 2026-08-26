import {render, screen} from 'src/test-utils';
import {MemoryRouter} from 'react-router-dom';
import BuildLogs from './BuildLogs';

const mockUseQuayConfigWithLoading = vi.fn();
const mockUseCurrentUser = vi.fn();

vi.mock('src/hooks/UseQuayConfig', () => ({
  useQuayConfigWithLoading: (...args: unknown[]) =>
    mockUseQuayConfigWithLoading(...args),
  useQuayConfig: () => ({features: {BUILD_SUPPORT: true}}),
}));

vi.mock('src/hooks/UseCurrentUser', () => ({
  useCurrentUser: (...args: unknown[]) => mockUseCurrentUser(...args),
  useUpdateUser: vi.fn(),
}));

vi.mock('src/hooks/UseSuperuserPermissions', () => ({
  useSuperuserPermissions: () => ({
    isSuperUser: true,
    canModify: true,
    isReadOnlySuperUser: false,
    inReadOnlyMode: false,
  }),
}));

vi.mock('src/hooks/UseBuildLogs', () => ({
  useFetchBuildLogsSuperuser: () => ({
    data: null,
    isLoading: false,
    isError: false,
    error: null,
  }),
}));

function renderComponent() {
  return render(
    <MemoryRouter>
      <BuildLogs />
    </MemoryRouter>,
  );
}

describe('BuildLogs', () => {
  afterEach(() => {
    vi.clearAllMocks();
  });

  it('shows spinner while config is loading', () => {
    mockUseQuayConfigWithLoading.mockReturnValue({
      config: null,
      isLoading: true,
      error: null,
    });
    mockUseCurrentUser.mockReturnValue({
      user: {super_user: true},
      loading: false,
      error: null,
    });

    renderComponent();
    expect(screen.getByLabelText('Loading')).toBeInTheDocument();
    expect(screen.queryByText('Build Logs')).not.toBeInTheDocument();
  });

  it('shows spinner while user is loading', () => {
    mockUseQuayConfigWithLoading.mockReturnValue({
      config: {features: {BUILD_SUPPORT: true}},
      isLoading: false,
      error: null,
    });
    mockUseCurrentUser.mockReturnValue({
      user: null,
      loading: true,
      error: null,
    });

    renderComponent();
    expect(screen.getByLabelText('Loading')).toBeInTheDocument();
    expect(screen.queryByText('Build Logs')).not.toBeInTheDocument();
  });

  it('renders the build logs page after loading completes', () => {
    mockUseQuayConfigWithLoading.mockReturnValue({
      config: {features: {BUILD_SUPPORT: true}},
      isLoading: false,
      error: null,
    });
    mockUseCurrentUser.mockReturnValue({
      user: {super_user: true},
      loading: false,
      error: null,
    });

    renderComponent();
    expect(screen.queryByLabelText('Loading')).not.toBeInTheDocument();
    expect(screen.getByText('Build Logs')).toBeInTheDocument();
  });
});
