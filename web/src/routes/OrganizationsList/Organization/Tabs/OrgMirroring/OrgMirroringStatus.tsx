import React, {useState} from 'react';
import {
  Divider,
  Button,
  Label,
  LabelGroup,
  Modal,
  ModalVariant,
  ModalHeader,
  ModalBody,
  ModalFooter,
} from '@patternfly/react-core';
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
  isCancellingSync: boolean;
  onCancelSync: () => Promise<void>;
  onVerifyConnection: () => Promise<void>;
}

export const OrgMirroringStatus: React.FC<OrgMirroringStatusProps> = ({
  config,
  isVerifying,
  isCancellingSync,
  onCancelSync,
  onVerifyConnection,
}) => {
  const [isCancelModalOpen, setIsCancelModalOpen] = useState(false);

  if (!config) {
    return null;
  }

  return (
    <>
      <Modal
        variant={ModalVariant.small}
        isOpen={isCancelModalOpen}
        onClose={() => setIsCancelModalOpen(false)}
      >
        <ModalHeader title="Cancel sync" />
        <ModalBody>
          Are you sure you want to cancel the current sync operation? Future
          scheduled syncs will continue as normal.
        </ModalBody>
        <ModalFooter>
          <Button
            key="confirm"
            variant="danger"
            onClick={async () => {
              setIsCancelModalOpen(false);
              await onCancelSync();
            }}
            data-testid="confirm-cancel-sync-button"
          >
            Yes, cancel sync
          </Button>
          <Button
            key="cancel"
            variant="link"
            onClick={() => setIsCancelModalOpen(false)}
          >
            Cancel
          </Button>
        </ModalFooter>
      </Modal>
      <Divider />
      <StatusDisplay
        title="Status"
        data-testid="org-mirror-status-display"
        items={[
          {
            label: 'State',
            value: config.repo_sync_status_counts ? (
              <LabelGroup numLabels={10}>
                {Object.entries(config.repo_sync_status_counts)
                  .filter(([, count]) => count > 0)
                  .map(([status, count]) => (
                    <Label
                      key={status}
                      color={orgMirrorStatusColors[status] || 'grey'}
                    >
                      {orgMirrorStatusLabels[status] || status}: {count}
                    </Label>
                  ))}
                {Object.values(config.repo_sync_status_counts).every(
                  (c) => c === 0,
                ) && 'No repositories'}
              </LabelGroup>
            ) : (
              'N/A'
            ),
            action: (
              <Button
                variant="danger"
                size="sm"
                type="button"
                isDisabled={
                  isCancellingSync ||
                  !config.repo_sync_status_counts ||
                  ((config.repo_sync_status_counts['SYNCING'] ?? 0) === 0 &&
                    (config.repo_sync_status_counts['SYNC_NOW'] ?? 0) === 0)
                }
                isLoading={isCancellingSync}
                data-testid="cancel-sync-button"
                onClick={() => setIsCancelModalOpen(true)}
              >
                {isCancellingSync ? 'Cancelling...' : 'Cancel Sync'}
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
