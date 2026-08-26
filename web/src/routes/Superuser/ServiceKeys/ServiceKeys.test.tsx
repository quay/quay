import {render, screen, userEvent, waitFor} from 'src/test-utils';
import {MemoryRouter} from 'react-router-dom';
import ServiceKeys from './ServiceKeys';
import {fetchServiceKeys, IServiceKey} from 'src/resources/ServiceKeysResource';

vi.mock('src/resources/ServiceKeysResource', () => ({
  fetchServiceKeys: vi.fn(),
  createServiceKey: vi.fn(),
  updateServiceKey: vi.fn(),
  deleteServiceKey: vi.fn(),
  approveServiceKey: vi.fn(),
}));

vi.mock('src/hooks/UseCurrentUser', () => ({
  useCurrentUser: () => ({
    isSuperUser: true,
    loading: false,
    error: null,
    user: {super_user: true, global_readonly_super_user: false},
  }),
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

vi.mock('src/components/breadcrumb/Breadcrumb', () => ({
  QuayBreadcrumb: () => null,
}));

const mockKeys: IServiceKey[] = [
  {
    kid: 'kid1',
    name: 'Alpha Key',
    service: 'alpha-service',
    created_date: '2024-01-01T00:00:00Z',
  },
  {
    kid: 'kid2',
    name: 'Beta Key',
    service: 'beta-service',
    created_date: '2024-01-02T00:00:00Z',
  },
];

function renderComponent() {
  return render(
    <MemoryRouter>
      <ServiceKeys />
    </MemoryRouter>,
  );
}

describe('ServiceKeys filter', () => {
  beforeEach(() => {
    vi.mocked(fetchServiceKeys).mockResolvedValue(mockKeys);
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  it('renders all keys initially', async () => {
    renderComponent();
    await waitFor(() => {
      expect(screen.getByText('Alpha Key')).toBeInTheDocument();
      expect(screen.getByText('Beta Key')).toBeInTheDocument();
    });
  });

  it('filters displayed keys when text is typed in search input', async () => {
    const user = userEvent.setup();
    renderComponent();

    await waitFor(() => {
      expect(screen.getByText('Alpha Key')).toBeInTheDocument();
    });

    const searchInput = screen.getByTestId('service-keys-search');
    await user.type(searchInput, 'alpha');

    await waitFor(() => {
      expect(screen.queryByText('Beta Key')).not.toBeInTheDocument();
    });
    expect(screen.getByText('Alpha Key')).toBeInTheDocument();
  });

  it('filters by service name', async () => {
    const user = userEvent.setup();
    renderComponent();

    await waitFor(() => {
      expect(screen.getByText('Beta Key')).toBeInTheDocument();
    });

    const searchInput = screen.getByTestId('service-keys-search');
    await user.type(searchInput, 'beta-service');

    await waitFor(() => {
      expect(screen.queryByText('Alpha Key')).not.toBeInTheDocument();
    });
    expect(screen.getByText('Beta Key')).toBeInTheDocument();
  });

  it('supports multi-word key names in search', async () => {
    const user = userEvent.setup();
    renderComponent();

    await waitFor(() => {
      expect(screen.getByText('Alpha Key')).toBeInTheDocument();
    });

    const searchInput = screen.getByTestId('service-keys-search');
    await user.type(searchInput, 'Alpha Key');

    await waitFor(() => {
      expect(screen.queryByText('Beta Key')).not.toBeInTheDocument();
    });
    expect(screen.getByText('Alpha Key')).toBeInTheDocument();
  });
});
