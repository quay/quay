import userEvent from '@testing-library/user-event';
import {render, screen, within} from 'src/test-utils';
import {QuotaManagement} from './QuotaManagement';

const mockUpdateLimitMutation = vi.hoisted(() => vi.fn());
// Stable across renders: the component resets its limit state whenever
// organizationQuota changes identity.
const mockQuota = vi.hoisted(() => ({
  id: 'quota1',
  limit_bytes: 1073741824,
  limits: [
    {id: 'warn', type: 'Warning', limit_percent: 70},
    {id: 'reject', type: 'Reject', limit_percent: 90},
  ],
}));

vi.mock('src/hooks/UseQuotaManagement', () => ({
  useFetchOrganizationQuota: () => ({
    organizationQuota: mockQuota,
    isLoadingQuotas: false,
  }),
  useCreateOrganizationQuota: () => ({createQuotaMutation: vi.fn()}),
  useUpdateOrganizationQuota: () => ({updateQuotaMutation: vi.fn()}),
  useDeleteOrganizationQuota: () => ({deleteQuotaMutation: vi.fn()}),
  useCreateQuotaLimit: () => ({createLimitMutation: vi.fn()}),
  useUpdateQuotaLimit: () => ({updateLimitMutation: mockUpdateLimitMutation}),
  useDeleteQuotaLimit: () => ({deleteLimitMutation: vi.fn()}),
}));

vi.mock('src/hooks/UseCurrentUser', () => ({
  useCurrentUser: () => ({user: {username: 'admin'}}),
}));

vi.mock('src/hooks/UseSuperuserPermissions', () => ({
  useSuperuserPermissions: () => ({canModify: true}),
}));

describe('QuotaManagement limit update', () => {
  it('blocks updating a limit to Reject when another Reject exists', async () => {
    const user = userEvent.setup();
    render(
      <QuotaManagement
        organizationName="myorg"
        isUser={false}
        view="super-user"
      />,
    );

    const warnRow = within(screen.getByTestId('quota-limit-warn'));
    await user.click(warnRow.getByRole('button', {name: 'Warning'}));
    await user.click(screen.getByRole('option', {name: 'Reject'}));
    await user.click(warnRow.getByTestId('update-limit-button'));

    expect(
      await screen.findByText(
        'Error: A quota policy should only have a single reject threshold.',
      ),
    ).toBeInTheDocument();
    expect(mockUpdateLimitMutation).not.toHaveBeenCalled();
  });
});

describe('QuotaManagement limit threshold validation', () => {
  const message = 'Enter a whole number between 1 and 100.';

  it('shows an error for an out-of-range new limit threshold', async () => {
    const user = userEvent.setup();
    render(
      <QuotaManagement
        organizationName="myorg"
        isUser={false}
        view="super-user"
      />,
    );

    const input = screen.getByTestId('new-limit-percent-input');
    await user.type(input, '0');
    expect(screen.getByText(message)).toBeInTheDocument();

    await user.clear(input);
    await user.type(input, '101');
    expect(screen.getByText(message)).toBeInTheDocument();

    await user.clear(input);
    await user.type(input, '50');
    expect(screen.queryByText(message)).not.toBeInTheDocument();
  });

  it('shows an error for an out-of-range existing limit threshold', async () => {
    const user = userEvent.setup();
    render(
      <QuotaManagement
        organizationName="myorg"
        isUser={false}
        view="super-user"
      />,
    );

    const warnRow = within(screen.getByTestId('quota-limit-warn'));
    const input = warnRow.getByTestId('limit-percent-input');
    await user.clear(input);
    await user.type(input, '0');
    expect(warnRow.getByText(message)).toBeInTheDocument();

    await user.type(input, '5');
    expect(warnRow.queryByText(message)).not.toBeInTheDocument();
  });
});
