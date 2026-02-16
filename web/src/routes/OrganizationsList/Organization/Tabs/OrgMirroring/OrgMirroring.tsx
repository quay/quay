import React from 'react';
import {OrgMirroringConfiguration} from './OrgMirroringConfiguration';
import {OrgMirroringCredentials} from './OrgMirroringCredentials';
import {OrgMirroringFilters} from './OrgMirroringFilters';
import {OrgMirroringAdvancedSettings} from './OrgMirroringAdvancedSettings';
import {OrgMirroringStatus} from './OrgMirroringStatus';
import {OrgMirroringRepos} from './OrgMirroringRepos';
import {useOrgMirroringConfig} from 'src/hooks/UseOrgMirroringConfig';
import {
  useOrgMirroringForm,
  defaultFormValues,
} from 'src/hooks/UseOrgMirroringForm';
import {OrgMirroringFormData} from './types';
import {
  Form,
  Button,
  ButtonVariant,
  ActionGroup,
  Divider,
  Spinner,
  SelectOption,
  SelectGroup,
  Modal,
  ModalVariant,
  Text,
  TextContent,
} from '@patternfly/react-core';
import {DesktopIcon} from '@patternfly/react-icons';
import {useUI, AlertVariant} from 'src/contexts/UIContext';
import FormError from 'src/components/errors/FormError';
import {useFetchRobotAccounts} from 'src/hooks/useRobotAccounts';
import {useQuayConfig} from 'src/hooks/UseQuayConfig';
import {Entity} from 'src/resources/UserResource';
import {useQueryClient} from '@tanstack/react-query';
import {deleteOrgMirrorConfig} from 'src/resources/OrgMirrorResource';
import {CreateRobotModalWrapper} from './CreateRobotModalWrapper';
import {useSearchParams} from 'react-router-dom';

interface OrgMirroringProps {
  orgName: string;
}

export const OrgMirroring: React.FC<OrgMirroringProps> = ({orgName}) => {
  const {addAlert} = useUI();
  const queryClient = useQueryClient();
  const [isDeleteModalOpen, setIsDeleteModalOpen] = React.useState(false);
  const [searchParams, setSearchParams] = useSearchParams();

  // Initialize form hook (no external dependencies)
  const formHook = useOrgMirroringForm();

  // Initialize config hook
  const configHook = useOrgMirroringConfig(
    orgName,
    formHook.reset,
    formHook.setSelectedRobot,
  );

  // Form submission handler - composes both hooks without circular dependency
  const onSubmit = async (data: OrgMirroringFormData) => {
    try {
      await configHook.submitConfig(data);
      formHook.reset({...data, password: ''});
      addAlert({
        variant: AlertVariant.Success,
        title: 'Organization mirror configuration saved successfully',
      });
    } catch (err: unknown) {
      addAlert({
        variant: AlertVariant.Failure,
        title: 'Error saving organization mirror configuration',
        message: (err as Error).message,
      });
    }
  };

  // Fetch robot accounts
  const {robots} = useFetchRobotAccounts(orgName);
  const quayConfig = useQuayConfig();
  const robotsDisallowed = quayConfig?.config?.ROBOTS_DISALLOW === true;

  // Create dropdown options for robot selector
  const robotOptions = [
    <React.Fragment key="dropdown-options">
      {!robotsDisallowed && (
        <>
          <SelectOption
            key="create-robot"
            component="button"
            onClick={() => formHook.setIsCreateRobotModalOpen(true)}
          >
            <DesktopIcon /> &nbsp; Create robot account
          </SelectOption>
          <Divider component="li" key="divider" />
        </>
      )}
      <SelectGroup label="Robot accounts" key="robot-accounts">
        {robots?.map(({name}) => (
          <SelectOption
            key={name}
            value={name}
            onClick={() => formHook.handleRobotSelect(name)}
          >
            {name}
          </SelectOption>
        ))}
      </SelectGroup>
    </React.Fragment>,
  ];

  if (configHook.isLoading) {
    return <Spinner size="md" />;
  }

  if (configHook.error) {
    return (
      <FormError
        message={configHook.error}
        setErr={() => configHook.invalidateConfig()}
      />
    );
  }

  // When no config exists and user hasn't opted to set up, show the "state is NORMAL" message
  const isSetupMode = searchParams.get('setup') === 'true';
  if (!configHook.config && !isSetupMode) {
    return (
      <div className="pf-v5-u-max-width-lg pf-v5-u-p-md">
        <TextContent>
          <Text>
            This organization&apos;s state is <strong>NORMAL</strong>. Use the{' '}
            <Button
              variant="link"
              isInline
              onClick={() => setSearchParams({tab: 'Settings'})}
            >
              Settings tab
            </Button>{' '}
            and change it to <strong>Mirror</strong> to manage its mirroring
            configuration.
          </Text>
        </TextContent>
      </div>
    );
  }

  const handleDelete = async () => {
    try {
      await deleteOrgMirrorConfig(orgName);
      queryClient.invalidateQueries({queryKey: ['org-mirror-repos', orgName]});
      configHook.setConfig(null);
      formHook.reset(defaultFormValues);
      formHook.setSelectedRobot(null);
      addAlert({
        variant: AlertVariant.Success,
        title: 'Organization mirror configuration deleted successfully',
      });
    } catch (err: unknown) {
      addAlert({
        variant: AlertVariant.Failure,
        title: 'Error deleting organization mirror configuration',
        message: (err as Error).message,
      });
    } finally {
      setIsDeleteModalOpen(false);
    }
  };

  return (
    <div className="pf-v5-u-max-width-lg pf-v5-u-p-md">
      <Form
        isWidthLimited
        data-testid="org-mirror-form"
        onSubmit={formHook.handleSubmit(onSubmit)}
      >
        <OrgMirroringConfiguration
          control={formHook.control}
          errors={formHook.errors}
          isEnabled={formHook.isEnabled}
          config={configHook.config}
          orgName={orgName}
          selectedRobot={formHook.selectedRobot}
          setSelectedRobot={formHook.setSelectedRobot}
          robotOptions={robotOptions}
          isSyncingNow={configHook.isSyncingNow}
          onSyncNow={async () => {
            try {
              await configHook.handleSyncNow();
              addAlert({
                variant: AlertVariant.Success,
                title: 'Organization sync scheduled successfully',
              });
            } catch (err: unknown) {
              addAlert({
                variant: AlertVariant.Failure,
                title: 'Error scheduling sync',
                message: (err as Error).message,
              });
            }
          }}
          onToggleEnabled={async (checked, onChange) => {
            try {
              await configHook.handleToggleEnabled(checked);
              onChange(checked);
              addAlert({
                variant: AlertVariant.Success,
                title: `Organization mirror ${
                  checked ? 'enabled' : 'disabled'
                } successfully`,
              });
            } catch (err: unknown) {
              addAlert({
                variant: AlertVariant.Failure,
                title: 'Error toggling organization mirror',
                message: (err as Error).message,
              });
            }
          }}
          addAlert={addAlert}
        />
        <OrgMirroringFilters
          control={formHook.control}
          errors={formHook.errors}
        />
        <OrgMirroringCredentials
          control={formHook.control}
          errors={formHook.errors}
          config={configHook.config}
        />
        <OrgMirroringAdvancedSettings
          control={formHook.control}
          errors={formHook.errors}
          config={configHook.config}
        />
        <OrgMirroringStatus
          config={configHook.config}
          isVerifying={configHook.isVerifying}
          onCancelSync={async () => {
            try {
              await configHook.handleCancelSync();
              addAlert({
                variant: AlertVariant.Success,
                title: 'Sync cancelled successfully',
              });
            } catch (err: unknown) {
              addAlert({
                variant: AlertVariant.Failure,
                title: 'Error cancelling sync',
                message: (err as Error).message,
              });
            }
          }}
          onVerifyConnection={async () => {
            try {
              const result = await configHook.handleVerifyConnection();
              if (result.success) {
                addAlert({
                  variant: AlertVariant.Success,
                  title: 'Connection verified successfully',
                  message: result.message,
                });
              } else {
                addAlert({
                  variant: AlertVariant.Failure,
                  title: 'Connection verification failed',
                  message: result.message,
                });
              }
            } catch (err: unknown) {
              addAlert({
                variant: AlertVariant.Failure,
                title: 'Error verifying connection',
                message: (err as Error).message,
              });
            }
          }}
        />
        <OrgMirroringRepos config={configHook.config} orgName={orgName} />
        <ActionGroup>
          <Button
            variant={ButtonVariant.primary}
            className="pf-v5-u-display-block pf-v5-u-mx-auto"
            type="submit"
            isDisabled={
              !formHook.isValid || (configHook.config && !formHook.isDirty)
            }
            data-testid="submit-button"
          >
            {configHook.config
              ? 'Update Organization Mirror'
              : 'Enable Organization Mirror'}
          </Button>
          {configHook.config && (
            <Button
              variant={ButtonVariant.danger}
              type="button"
              onClick={() => setIsDeleteModalOpen(true)}
              data-testid="delete-mirror-button"
            >
              Delete Mirror Configuration
            </Button>
          )}
        </ActionGroup>

        {/* Robot Creation Modal - only mounted when open to avoid unnecessary API calls */}
        {formHook.isCreateRobotModalOpen && (
          <CreateRobotModalWrapper
            isModalOpen={formHook.isCreateRobotModalOpen}
            handleModalToggle={() => formHook.setIsCreateRobotModalOpen(false)}
            orgName={orgName}
            setEntity={(robot: Entity) => {
              formHook.setSelectedRobot(robot);
              formHook.setValue('robotUsername', robot.name, {
                shouldDirty: true,
              });
              queryClient.invalidateQueries({queryKey: ['robots']});
            }}
            showSuccessAlert={(msg) =>
              addAlert({variant: AlertVariant.Success, title: msg})
            }
            showErrorAlert={(msg) =>
              addAlert({variant: AlertVariant.Failure, title: msg})
            }
          />
        )}

        {/* Delete Confirmation Modal */}
        <Modal
          variant={ModalVariant.small}
          title="Delete Mirror Configuration"
          isOpen={isDeleteModalOpen}
          onClose={() => setIsDeleteModalOpen(false)}
          actions={[
            <Button
              key="confirm"
              variant="danger"
              onClick={handleDelete}
              data-testid="confirm-delete-button"
            >
              Delete
            </Button>,
            <Button
              key="cancel"
              variant="link"
              onClick={() => setIsDeleteModalOpen(false)}
            >
              Cancel
            </Button>,
          ]}
        >
          Are you sure you want to delete the organization mirror configuration?
          This will stop all future syncs. Existing mirrored repositories will
          remain.
        </Modal>
      </Form>
    </div>
  );
};
