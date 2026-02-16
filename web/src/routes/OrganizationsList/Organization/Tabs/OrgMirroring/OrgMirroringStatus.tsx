import React from 'react';
import {Divider, Button, Label} from '@patternfly/react-core';
import {StatusDisplay} from 'src/components/StatusDisplay';
import {
  OrgMirrorConfig,
  orgMirrorStatusLabels,
  orgMirrorStatusColors,
} from 'src/resources/OrgMirrorResource';
import {formatDate} from 'src/libs/utils';

interface OrgMirroringStatusProps {
  config: OrgMirrorConfig | null;
  isVerifying: boolean;
  onCancelSync: () => Promise<void>;
  onVerifyConnection: () => Promise<void>;
}

export const OrgMirroringStatus: React.FC<OrgMirroringStatusProps> = ({
  config,
  isVerifying,
  onCancelSync,
  onVerifyConnection,
}) => {
  if (!config) {
    return null;
  }

  return (
    <>
      <Divider />
      <StatusDisplay
        title="Status"
        data-testid="org-mirror-status-display"
        items={[
          {
            label: 'State',
            value: (
              <Label color={orgMirrorStatusColors[config.sync_status]}>
                {orgMirrorStatusLabels[config.sync_status] ||
                  config.sync_status}
              </Label>
            ),
            action: (
              <Button
                variant="danger"
                size="sm"
                type="button"
                isDisabled={
                  config.sync_status !== 'SYNCING' &&
                  config.sync_status !== 'SYNC_NOW'
                }
                data-testid="cancel-sync-button"
                onClick={onCancelSync}
              >
                Cancel Sync
              </Button>
            ),
          },
          {
            label: 'Timeout',
            value: config.sync_expiration_date
              ? formatDate(config.sync_expiration_date)
              : 'None',
          },
          {
            label: 'Retries Remaining',
            value:
              config.sync_retries_remaining != null
                ? `${config.sync_retries_remaining} / 3`
                : '3 / 3',
          },
          {
            label: 'Connection',
            value: (
              <Button
                variant="secondary"
                size="sm"
                type="button"
                isLoading={isVerifying}
                isDisabled={isVerifying}
                data-testid="verify-connection-button"
                onClick={onVerifyConnection}
              >
                Verify Connection
              </Button>
            ),
          },
        ]}
      />
    </>
  );
};
