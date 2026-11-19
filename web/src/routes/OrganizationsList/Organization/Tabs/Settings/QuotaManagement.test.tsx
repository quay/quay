import {fireEvent} from '@testing-library/react';
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
  const message = 'Enter 1 to 100.';

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
    expect(
      screen.getByText(message).closest('.pf-v6-c-helper-text'),
    ).toHaveAttribute('aria-live', 'polite');
    expect(input).toHaveAttribute('aria-invalid', 'true');
    expect(input).toHaveAccessibleDescription(expect.stringContaining(message));

    await user.clear(input);
    await user.type(input, '101');
    expect(screen.getByText(message)).toBeInTheDocument();

    await user.clear(input);
    await user.type(input, '50');
    expect(screen.queryByText(message)).not.toBeInTheDocument();
    expect(input).not.toHaveAttribute('aria-describedby');
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
    expect(
      warnRow.getByText(message).closest('.pf-v6-c-helper-text'),
    ).toHaveAttribute('aria-live', 'polite');
    expect(input).toHaveAttribute('aria-invalid', 'true');
    expect(input).toHaveAccessibleDescription(expect.stringContaining(message));

    await user.type(input, '5');
    expect(warnRow.queryByText(message)).not.toBeInTheDocument();
    expect(input).not.toHaveAttribute('aria-describedby');
  });

  it('keeps an out-of-range existing threshold in the field', async () => {
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
    const update = warnRow.getByTestId('update-limit-button');
    await user.tripleClick(input);
    await user.keyboard('50');
    expect(update).toBeEnabled();

    await user.tripleClick(input);
    await user.keyboard('0');
    expect(input).toHaveValue(0);
    expect(warnRow.getByText(message)).toBeInTheDocument();
    expect(update).toBeDisabled();
  });

  it('keeps an out-of-range new threshold in the field', async () => {
    const user = userEvent.setup();
    render(
      <QuotaManagement
        organizationName="myorg"
        isUser={false}
        view="super-user"
      />,
    );

    await user.click(screen.getByTestId('new-limit-type-select'));
    await user.click(screen.getByRole('option', {name: 'Warning'}));
    const input = screen.getByTestId('new-limit-percent-input');
    const add = screen.getByTestId('add-limit-button');
    await user.type(input, '50');
    expect(add).toBeEnabled();

    await user.tripleClick(input);
    await user.keyboard('0');
    expect(input).toHaveValue(0);
    expect(add).toBeDisabled();
  });

  it('flags a decimal new limit threshold', async () => {
    const user = userEvent.setup();
    render(
      <QuotaManagement
        organizationName="myorg"
        isUser={false}
        view="super-user"
      />,
    );

    await user.click(screen.getByTestId('new-limit-type-select'));
    await user.click(screen.getByRole('option', {name: 'Warning'}));
    await user.type(screen.getByTestId('new-limit-percent-input'), '5.5');
    expect(screen.getByText(message)).toBeInTheDocument();
    expect(screen.getByTestId('add-limit-button')).toBeDisabled();
  });

  it('flags a decimal existing limit threshold', async () => {
    const user = userEvent.setup();
    render(
      <QuotaManagement
        organizationName="myorg"
        isUser={false}
        view="super-user"
      />,
    );

    const warnRow = within(screen.getByTestId('quota-limit-warn'));
    await user.tripleClick(warnRow.getByTestId('limit-percent-input'));
    await user.keyboard('5.5');
    expect(warnRow.getByText(message)).toBeInTheDocument();
    expect(warnRow.getByTestId('update-limit-button')).toBeDisabled();
  });

  it('flags a cleared existing limit threshold', async () => {
    const user = userEvent.setup();
    render(
      <QuotaManagement
        organizationName="myorg"
        isUser={false}
        view="super-user"
      />,
    );

    const warnRow = within(screen.getByTestId('quota-limit-warn'));
    await user.clear(warnRow.getByTestId('limit-percent-input'));
    expect(warnRow.getByText(message)).toBeInTheDocument();
    expect(warnRow.getByTestId('update-limit-button')).toBeDisabled();
  });

  it('flags unparseable text but not an empty new threshold', async () => {
    const user = userEvent.setup();
    render(
      <QuotaManagement
        organizationName="myorg"
        isUser={false}
        view="super-user"
      />,
    );

    const input = screen.getByTestId('new-limit-percent-input');
    await user.type(input, '1');
    await user.clear(input);
    expect(screen.queryByText(message)).not.toBeInTheDocument();

    await user.type(input, '1');
    // A number input reports text like "1e" as '' with validity.badInput.
    Object.defineProperty(input, 'validity', {value: {badInput: true}});
    fireEvent.change(input, {target: {value: ''}});
    expect(screen.getByText(message)).toBeInTheDocument();
  });
});
