import {render, screen, userEvent} from 'src/test-utils';
import {AutoPruneMethod} from 'src/resources/NamespaceAutoPruneResource';
import RegistryAutoPruneNotice from './RegistryAutoPruneNotice';

const registryPolicy = {
  method: AutoPruneMethod.TAG_NUMBER,
  value: 20,
};

const policyScenarios = [
  {
    method: AutoPruneMethod.TAG_NUMBER,
    value: 20,
    label: 'Number of Tags',
  },
  {
    method: AutoPruneMethod.TAG_CREATION_DATE,
    value: '7d',
    label: 'Age of Tags',
  },
];

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

  it.each(policyScenarios)(
    'shows $label policy details in a keyboard-focusable tooltip',
    async ({method, value, label}) => {
      const user = userEvent.setup();
      render(
        <RegistryAutoPruneNotice
          isAutoPruneEnabled={true}
          policy={{method, value}}
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
        `Tags will be pruned across eligible repositories with the policy method: ${label} and value: ${value}. Read-only, mirrored, and marked-for-deletion repositories are excluded.`,
      );
    },
  );
});
