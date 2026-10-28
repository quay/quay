import {Alert, Button, Tooltip} from '@patternfly/react-core';
import {InfoCircleIcon} from '@patternfly/react-icons';
import type {NamespaceAutoPrunePolicy} from 'src/resources/NamespaceAutoPruneResource';

export default function RegistryAutoPruneNotice(
  props: RegistryAutoPruneNoticeProps,
) {
  if (!props.isAutoPruneEnabled || props.policy == null) {
    return null;
  }

  const tooltipContent = `Tags will be pruned across eligible repositories with the policy method: ${props.policy.method} and value: ${props.policy.value}. Read-only, mirrored, and marked-for-deletion repositories are excluded.`;

  return (
    <Alert
      isInline
      variant="warning"
      className="pf-v6-u-mb-md"
      data-testid="registry-autoprune-notice"
      title={
        <>
          Registry wide autopruning is in effect{' '}
          <Tooltip content={tooltipContent}>
            <Button
              aria-label="Registry-wide auto-prune policy details"
              type="button"
              variant="plain"
            >
              <InfoCircleIcon />
            </Button>
          </Tooltip>
        </>
      }
    />
  );
}

interface RegistryAutoPruneNoticeProps {
  isAutoPruneEnabled: boolean;
  policy?: NamespaceAutoPrunePolicy | null;
}
