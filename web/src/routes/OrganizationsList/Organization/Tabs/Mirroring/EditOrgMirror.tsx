import {
  Alert,
  Button,
  DescriptionList,
  DescriptionListDescription,
  DescriptionListGroup,
  DescriptionListTerm,
  Divider,
  Flex,
  FlexItem,
  Label,
  Title,
} from '@patternfly/react-core';
import {SyncAltIcon} from '@patternfly/react-icons';
import {useEffect} from 'react';
import {AlertVariant, useUI} from 'src/contexts/UIContext';
import {
  useDeleteOrgMirrorConfig,
  useTriggerOrgMirrorSync,
  useUpdateOrgMirrorConfig,
} from 'src/hooks/UseOrgMirror';
import {
  OrgMirrorConfig,
  OrgMirrorConfigResponse,
  syncStatusLabels,
} from 'src/resources/OrgMirrorResource';
import OrgMirrorForm from './OrgMirrorForm';
import SyncStatusDashboard from './SyncStatusDashboard';
import Alerts from 'src/routes/Alerts';

interface EditOrgMirrorProps {
  organizationName: string;
  mirrorConfig: OrgMirrorConfigResponse;
}

function getSyncStatusColor(
  status: OrgMirrorConfigResponse['sync_status'],
): 'green' | 'red' | 'blue' | 'orange' | 'grey' {
  switch (status) {
    case 'SUCCESS':
      return 'green';
    case 'FAIL':
      return 'red';
    case 'SYNCING':
    case 'SYNC_NOW':
      return 'blue';
    case 'CANCEL':
      return 'orange';
    default:
      return 'grey';
  }
}

export default function EditOrgMirror({
  organizationName,
  mirrorConfig,
}: EditOrgMirrorProps) {
  const {addAlert, clearAllAlerts} = useUI();

  const {updateMirrorConfig, isUpdating} = useUpdateOrgMirrorConfig(
    organizationName,
    {
      onSuccess: () => {
        addAlert({
          variant: AlertVariant.Success,
          title: 'Organization mirror configuration updated successfully',
        });
      },
      onError: (error) => {
        addAlert({
          variant: AlertVariant.Failure,
          title: error,
        });
      },
    },
  );

  const {deleteMirrorConfig, isDeleting} = useDeleteOrgMirrorConfig(
    organizationName,
    {
      onSuccess: () => {
        addAlert({
          variant: AlertVariant.Success,
          title: 'Organization mirror configuration deleted successfully',
        });
      },
      onError: (error) => {
        addAlert({
          variant: AlertVariant.Failure,
          title: error,
        });
      },
    },
  );

  const {triggerSync, isSyncing} = useTriggerOrgMirrorSync(organizationName, {
    onSuccess: () => {
      addAlert({
        variant: AlertVariant.Success,
        title: 'Sync triggered successfully',
      });
    },
    onError: (error) => {
      addAlert({
        variant: AlertVariant.Failure,
        title: error,
      });
    },
  });

  useEffect(() => {
    return () => {
      clearAllAlerts();
    };
  }, []);

  const handleSubmit = async (config: OrgMirrorConfig) => {
    updateMirrorConfig(config);
  };

  const handleDelete = () => {
    if (
      window.confirm(
        'Are you sure you want to delete this organization mirror configuration? This action cannot be undone.',
      )
    ) {
      deleteMirrorConfig();
    }
  };

  const handleSyncNow = () => {
    triggerSync();
  };

  const isSyncInProgress =
    mirrorConfig.sync_status === 'SYNCING' ||
    mirrorConfig.sync_status === 'SYNC_NOW';

  return (
    <>
      <Title headingLevel="h3" style={{marginBottom: '1rem'}}>
        Organization Mirror Configuration
      </Title>

      {/* Sync Status Section */}
      <Alert
        variant={mirrorConfig.sync_status === 'FAIL' ? 'danger' : 'info'}
        isInline
        title="Mirror Status"
        style={{marginBottom: '1.5rem'}}
      >
        <DescriptionList isHorizontal isCompact>
          <DescriptionListGroup>
            <DescriptionListTerm>Status</DescriptionListTerm>
            <DescriptionListDescription>
              <Label color={getSyncStatusColor(mirrorConfig.sync_status)}>
                {syncStatusLabels[mirrorConfig.sync_status]}
              </Label>
            </DescriptionListDescription>
          </DescriptionListGroup>
          <DescriptionListGroup>
            <DescriptionListTerm>Source</DescriptionListTerm>
            <DescriptionListDescription>
              {mirrorConfig.external_reference}
            </DescriptionListDescription>
          </DescriptionListGroup>
          {mirrorConfig.sync_expiration_date && (
            <DescriptionListGroup>
              <DescriptionListTerm>Next Sync</DescriptionListTerm>
              <DescriptionListDescription>
                {new Date(mirrorConfig.sync_expiration_date).toLocaleString()}
              </DescriptionListDescription>
            </DescriptionListGroup>
          )}
          {mirrorConfig.sync_retries_remaining !== null &&
            mirrorConfig.sync_retries_remaining !== undefined && (
              <DescriptionListGroup>
                <DescriptionListTerm>Retries Remaining</DescriptionListTerm>
                <DescriptionListDescription>
                  {mirrorConfig.sync_retries_remaining}
                </DescriptionListDescription>
              </DescriptionListGroup>
            )}
        </DescriptionList>
        <Flex style={{marginTop: '1rem'}}>
          <FlexItem>
            <Button
              variant="secondary"
              icon={<SyncAltIcon />}
              onClick={handleSyncNow}
              isLoading={isSyncing}
              isDisabled={
                isSyncing || isSyncInProgress || !mirrorConfig.is_enabled
              }
              data-testid="sync-now-btn"
            >
              Sync Now
            </Button>
          </FlexItem>
        </Flex>
      </Alert>

      <Divider style={{marginBottom: '1.5rem'}} />

      <OrgMirrorForm
        organizationName={organizationName}
        existingConfig={mirrorConfig}
        onSubmit={handleSubmit}
        onDelete={handleDelete}
        isSubmitting={isUpdating}
        isDeleting={isDeleting}
        submitLabel="Update"
      />

      {/* Sync Status Dashboard with Discovered Repos */}
      <SyncStatusDashboard
        organizationName={organizationName}
        mirrorConfig={mirrorConfig}
      />

      <Alerts />
    </>
  );
}
