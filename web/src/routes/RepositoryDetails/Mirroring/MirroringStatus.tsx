import React from 'react';
import {Divider, Button} from '@patternfly/react-core';
import {StatusDisplay} from 'src/components/StatusDisplay';
import {AlertVariant} from 'src/contexts/UIContext';
import {
  MirroringConfigResponse,
  getMirrorConfig,
  cancelSync,
  statusLabels,
} from 'src/resources/MirroringResource';

interface MirroringStatusProps {
  config: MirroringConfigResponse | null;
  namespace: string;
  repoName: string;
  setConfig: (config: MirroringConfigResponse) => void;
  addAlert: (alert: {
    variant: AlertVariant;
    title: string;
    message?: string;
  }) => void;
}

export const MirroringStatus: React.FC<MirroringStatusProps> = ({
  config,
  namespace,
  repoName,
  setConfig,
  addAlert,
}) => {
  if (!config) {
    return null;
  }

  return (
    <>
      <Divider />
      <StatusDisplay
        title="Status"
        data-testid="mirror-status-display"
        items={[
          {
            label: 'State',
            value: statusLabels[config.sync_status] || config.sync_status,
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
                onClick={async () => {
                  try {
                    await cancelSync(namespace, repoName);
                    addAlert({
                      variant: AlertVariant.Success,
                      title: 'Sync cancelled successfully',
                    });
                    const response = await getMirrorConfig(namespace, repoName);
                    setConfig(response);
                  } catch (err) {
                    addAlert({
                      variant: AlertVariant.Failure,
                      title: 'Error cancelling sync',
                      message: err.message,
                    });
                  }
                }}
              >
                Cancel
              </Button>
            ),
          },
          {
            label: 'Timeout',
            value: config.sync_expiration_date || 'None',
          },
          {
            label: 'Retries Remaining',
            value:
              config.sync_retries_remaining != null
                ? `${config.sync_retries_remaining} / 3`
                : '3 / 3',
          },
        ]}
      />
    </>
  );
};
