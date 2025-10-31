import React from 'react';
import {MirroringHeader} from './MirroringHeader';
import {MirroringConfiguration} from './MirroringConfiguration';
import {MirroringCredentials} from './MirroringCredentials';
import {MirroringAdvancedSettings} from './MirroringAdvancedSettings';
import {MirroringStatus} from './MirroringStatus';
import {MirroringModals} from './MirroringModals';
import {useMirroringConfig} from 'src/hooks/UseMirroringConfig';
import {useMirroringForm} from 'src/hooks/UseMirroringForm';
import {
  Form,
  Button,
  ButtonVariant,
  ActionGroup,
  Divider,
  Text,
  TextContent,
  SelectOption,
  SelectGroup,
  Spinner,
} from '@patternfly/react-core';
import {DesktopIcon, UsersIcon} from '@patternfly/react-icons';
import {useRepository} from 'src/hooks/UseRepository';
import {useAlerts} from 'src/hooks/UseAlerts';
import FormError from 'src/components/errors/FormError';
import {useFetchRobotAccounts} from 'src/hooks/useRobotAccounts';
import {useFetchTeams} from 'src/hooks/UseTeams';
import {Entity} from 'src/resources/UserResource';
import {useQueryClient} from '@tanstack/react-query';
import './Mirroring.css';

interface MirroringProps {
  namespace: string;
  repoName: string;
}

export const Mirroring: React.FC<MirroringProps> = ({namespace, repoName}) => {
  const {
    repoDetails,
    errorLoadingRepoDetails,
    isLoading: isLoadingRepo,
  } = useRepository(namespace, repoName);
  const {addAlert} = useAlerts();
  const queryClient = useQueryClient();

  // Initialize form hook
  const formHook = useMirroringForm(
    async (data) => {
      await configHook.submitConfig(data);
    },
    addAlert,
    (error) => configHook.setError(error),
  );

  // Initialize config hook
  const configHook = useMirroringConfig(
    namespace,
    repoName,
    repoDetails?.state,
    formHook.reset,
    formHook.setSelectedRobot,
  );

  // Fetch robot accounts and teams
  const {robots} = useFetchRobotAccounts(namespace);
  const {teams} = useFetchTeams(namespace);

  // Create dropdown options
  const robotOptions = [
    <React.Fragment key="dropdown-options">
      <SelectOption
        key="create-robot"
        component="button"
        onClick={() => formHook.setIsCreateRobotModalOpen(true)}
      >
        <DesktopIcon /> &nbsp; Create robot account
      </SelectOption>
      <Divider component="li" key="divider" />
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

  if (isLoadingRepo) {
    return <Spinner size="md" />;
  }

  if (errorLoadingRepoDetails) {
    return (
      <FormError
        message={
          typeof errorLoadingRepoDetails === 'object' &&
          errorLoadingRepoDetails !== null &&
          'message' in errorLoadingRepoDetails
            ? String(errorLoadingRepoDetails.message)
            : 'Error loading repository'
        }
        setErr={configHook.setError}
      />
    );
  }

  if (!repoDetails) {
    return <Text>Repository not found</Text>;
  }

  if (repoDetails.state !== 'MIRROR') {
    return (
      <div className="pf-v5-u-max-width-lg pf-v5-u-p-md">
        <TextContent>
          <Text>
            This repository&apos;s state is <strong>{repoDetails.state}</strong>
            . Use the settings tab and change it to <strong>Mirror</strong> to
            manage its mirroring configuration.
          </Text>
        </TextContent>
      </div>
    );
  }

  if (configHook.isLoading) {
    return <Spinner size="md" />;
  }

  if (configHook.error) {
    return (
      <FormError message={configHook.error} setErr={configHook.setError} />
    );
  }

  return (
    <div className="pf-v5-u-max-width-lg pf-v5-u-p-md">
      <Form
        isWidthLimited
        data-testid="mirror-form"
        onSubmit={formHook.handleSubmit(formHook.onSubmit)}
      >
        <MirroringHeader
          namespace={namespace}
          repoName={repoName}
          isConfigured={!!configHook.config}
        />
        <Divider className="pf-v5-u-mt-sm" />
        <MirroringConfiguration
          control={formHook.control}
          errors={formHook.errors}
          formValues={formHook.formValues}
          config={configHook.config}
          namespace={namespace}
          repoName={repoName}
          selectedRobot={formHook.selectedRobot}
          setSelectedRobot={formHook.setSelectedRobot}
          isSelectOpen={formHook.isSelectOpen}
          setIsSelectOpen={formHook.setIsSelectOpen}
          isHovered={formHook.isHovered}
          setIsHovered={formHook.setIsHovered}
          robotOptions={robotOptions}
          setConfig={configHook.setConfig}
          addAlert={addAlert}
        />
        <MirroringCredentials
          control={formHook.control}
          errors={formHook.errors}
          config={configHook.config}
        />
        <MirroringAdvancedSettings
          control={formHook.control}
          errors={formHook.errors}
          config={configHook.config}
        />
        <MirroringStatus
          config={configHook.config}
          namespace={namespace}
          repoName={repoName}
          setConfig={configHook.setConfig}
          addAlert={addAlert}
        />
        <ActionGroup>
          <Button
            variant={ButtonVariant.primary}
            className="pf-v5-u-display-block pf-v5-u-mx-auto"
            type="button"
            onClick={() => formHook.onSubmit(formHook.formValues)}
            isDisabled={
              (configHook.config && !formHook.isDirty) ||
              !formHook.formValues.externalReference?.trim() ||
              !formHook.formValues.tags?.trim() ||
              (configHook.config &&
                !formHook.formValues.syncStartDate?.trim()) ||
              !formHook.formValues.syncValue?.trim() ||
              !formHook.formValues.robotUsername?.trim() ||
              !formHook.formValues.skopeoTimeoutInterval ||
              formHook.formValues.skopeoTimeoutInterval < 300 ||
              formHook.formValues.skopeoTimeoutInterval > 43200
            }
            data-testid="submit-button"
          >
            {configHook.config ? 'Update Mirror' : 'Enable Mirror'}
          </Button>
        </ActionGroup>
        <MirroringModals
          isCreateRobotModalOpen={formHook.isCreateRobotModalOpen}
          setIsCreateRobotModalOpen={formHook.setIsCreateRobotModalOpen}
          isCreateTeamModalOpen={formHook.isCreateTeamModalOpen}
          setIsCreateTeamModalOpen={formHook.setIsCreateTeamModalOpen}
          teamName={formHook.teamName}
          setTeamName={formHook.setTeamName}
          teamDescription={formHook.teamDescription}
          setTeamDescription={formHook.setTeamDescription}
          namespace={namespace}
          teams={teams}
          onRobotCreated={(robot: Entity) => {
            formHook.setSelectedRobot(robot);
            formHook.setValue('robotUsername', robot.name);
            // Invalidate robot cache to refresh the list
            queryClient.invalidateQueries(['robots']);
          }}
          onTeamCreated={(team: Entity) => {
            formHook.setSelectedRobot(team);
            formHook.setValue('robotUsername', team.name);
          }}
          addAlert={addAlert}
        />
      </Form>
    </div>
  );
};
