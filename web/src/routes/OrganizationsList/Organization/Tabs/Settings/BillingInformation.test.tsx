import {render, screen} from 'src/test-utils';
import {BillingInformation} from './BillingInformation';
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
  fetchMarketplaceSubscriptions: vi.fn(),
  setMarketplaceOrgAttachment: vi.fn(),
  setMarketplaceOrgRemoval: vi.fn(),
}));

describe('BillingInformation', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders when billing is enabled and marketplace is disabled', () => {
    render(<BillingInformation organizationName="testorg" />);

    expect(screen.getByTestId('billing-invoice-email')).toBeVisible();
    expect(fetchMarketplaceSubscriptions).not.toHaveBeenCalled();
  });
});
