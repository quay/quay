import {render, screen, userEvent} from 'src/test-utils';
import {AutoPruneMethod} from 'src/resources/NamespaceAutoPruneResource';
import RegistryAutoPruneNotice from './RegistryAutoPruneNotice';

const registryPolicy = {
  method: AutoPruneMethod.TAG_NUMBER,
  value: 20,
};

describe('RegistryAutoPruneNotice', () => {
  it.each([
    {
      isAutoPruneEnabled: false,
      policy: registryPolicy,
      reason: 'the auto-prune feature is disabled',
    },
    {
      isAutoPruneEnabled: true,
      policy: null,
      reason: 'the registry policy is not configured',
    },
  ])('does not render when $reason', ({isAutoPruneEnabled, policy}) => {
    render(
      <RegistryAutoPruneNotice
        isAutoPruneEnabled={isAutoPruneEnabled}
        policy={policy}
      />,
    );

    expect(
      screen.queryByTestId('registry-autoprune-notice'),
    ).not.toBeInTheDocument();
  });

  it('shows the policy details in a keyboard-focusable tooltip', async () => {
    const user = userEvent.setup();
    render(
      <RegistryAutoPruneNotice
        isAutoPruneEnabled={true}
        policy={registryPolicy}
      />,
    );

    expect(screen.getByTestId('registry-autoprune-notice')).toHaveTextContent(
      'Registry wide autopruning is in effect',
    );

    await user.tab();
    expect(
      screen.getByRole('button', {
        name: 'Registry-wide auto-prune policy details',
      }),
    ).toHaveFocus();
    expect(await screen.findByRole('tooltip')).toHaveTextContent(
      'Tags will be pruned across all repositories with the policy method: number_of_tags and value: 20',
    );
  });
});
