import {render, screen} from 'src/test-utils';
import {BillingInformation} from './BillingInformation';
import {MemoryRouter} from 'react-router-dom';
import {fetchMarketplaceSubscriptions} from 'src/resources/BillingResource';

vi.mock('src/hooks/UseCurrentUser', () => ({
  useCurrentUser: vi.fn(() => ({
    user: {
      username: 'testuser',
      invoice_email: false,
      invoice_email_address: '',
    },
  })),
  useUpdateUser: vi.fn(() => ({
    updateUser: vi.fn(),
    loading: false,
    error: null,
  })),
}));

vi.mock('src/hooks/UseOrganization', () => ({
  useOrganization: vi.fn(() => ({
    organization: {
      invoice_email: false,
      invoice_email_address: '',
    },
    isUserOrganization: false,
    loading: false,
  })),
}));

vi.mock('src/hooks/UseOrganizationSettings', () => ({
  useOrganizationSettings: vi.fn(() => ({updateOrgSettings: vi.fn()})),
}));

vi.mock('src/hooks/UseUpgradePlan', () => ({
  useUpgradePlan: vi.fn(() => ({
    currentPlan: {plan: 'free', usedPrivateRepos: 0},
    privateAllowed: false,
    privateCount: 0,
    upgrade: vi.fn(),
  })),
}));

vi.mock('src/hooks/UseRepositories', () => ({
  useRepositories: vi.fn(() => ({totalResults: 0})),
}));

vi.mock('src/hooks/UseQuayConfig', () => ({
  useQuayConfig: vi.fn(() => ({
    features: {BILLING: true, RH_MARKETPLACE: false},
  })),
}));

vi.mock('src/resources/BillingResource', () => ({
  fetchCard: vi.fn().mockResolvedValue(null),
  fetchInvoices: vi.fn().mockResolvedValue([]),
  createCardSetupSession: vi.fn(),
  fetchMarketplaceSubscriptions: vi.fn(),
  setMarketplaceOrgAttachment: vi.fn(),
  setMarketplaceOrgRemoval: vi.fn(),
}));

describe('BillingInformation', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders when billing is enabled and marketplace is disabled', () => {
    render(
      <MemoryRouter
        initialEntries={[
          '/organization/testorg?tab=Settings&settingsTab=billinginformation',
        ]}
      >
        <BillingInformation organizationName="testorg" />
      </MemoryRouter>,
    );

    expect(screen.getByRole('heading', {name: 'Invoices'})).toBeVisible();
    expect(
      screen.getByRole('button', {name: 'Invoice settings'}),
    ).toBeVisible();
    expect(
      screen.queryByTestId('billing-invoice-email'),
    ).not.toBeInTheDocument();
    expect(fetchMarketplaceSubscriptions).not.toHaveBeenCalled();
  });
});
