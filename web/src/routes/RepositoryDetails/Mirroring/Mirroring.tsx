import React, {useState, useEffect} from 'react';
import {useForm} from 'react-hook-form';

import {MirroringHeader} from './MirroringHeader';
import {MirroringConfiguration} from './MirroringConfiguration';
import {MirroringCredentials} from './MirroringCredentials';
import {MirroringAdvancedSettings} from './MirroringAdvancedSettings';
import {MirroringStatus} from './MirroringStatus';
import {MirroringFormData} from './types';
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
import {AlertVariant} from 'src/atoms/AlertState';
import FormError from 'src/components/errors/FormError';
import {useFetchRobotAccounts} from 'src/hooks/useRobotAccounts';
import {useFetchTeams} from 'src/hooks/UseTeams';
import CreateRobotAccountModal from 'src/components/modals/CreateRobotAccountModal';
import {CreateTeamModal} from 'src/routes/OrganizationsList/Organization/Tabs/DefaultPermissions/createPermissionDrawer/CreateTeamModal';
import {Entity, EntityKind} from 'src/resources/UserResource';
import {RepoPermissionDropdownItems} from 'src/routes/RepositoriesList/RobotAccountsList';
import {
  MirroringConfigResponse,
  getMirrorConfig,
  createMirrorConfig,
  updateMirrorConfig,
  timestampToISO,
  timestampFromISO,
} from 'src/resources/MirroringResource';
import {
  convertToSeconds,
  convertFromSeconds,
  formatDateForInput,
  validateTeamName,
} from 'src/libs/utils';
import './Mirroring.css';

interface MirroringProps {
  namespace: string;
  repoName: string;
}

// Default form values
const defaultFormValues: MirroringFormData = {
  isEnabled: true,
  externalReference: '',
  tags: '',
  syncStartDate: '',
  syncValue: '',
  syncUnit: 'minutes',
  robotUsername: '',
  username: '',
  password: '',
  verifyTls: true,
  httpProxy: '',
  httpsProxy: '',
  noProxy: '',
  unsignedImages: false,
};

export const Mirroring: React.FC<MirroringProps> = ({namespace, repoName}) => {
  const {
    repoDetails,
    errorLoadingRepoDetails,
    isLoading: isLoadingRepo,
  } = useRepository(namespace, repoName);
  const {addAlert} = useAlerts();

  // Initialize react-hook-form
  const form = useForm<MirroringFormData>({
    defaultValues: defaultFormValues,
    mode: 'onChange',
  });

  const {
    control,
    handleSubmit,
    formState: {errors, isValid, isDirty},
    setValue,
    watch,
    reset,
  } = form;

  // Watch all form values to maintain existing functionality
  const formValues = watch();

  // Non-form UI state
  const [selectedRobot, setSelectedRobot] = useState<Entity | null>(null);
  const [isSelectOpen, setIsSelectOpen] = useState(false);
  const [isHovered, setIsHovered] = useState(false);
  const [isCreateRobotModalOpen, setIsCreateRobotModalOpen] = useState(false);
  const [isCreateTeamModalOpen, setIsCreateTeamModalOpen] = useState(false);
  const [teamName, setTeamName] = useState('');
  const [teamDescription, setTeamDescription] = useState('');

  // Loading and error states
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [config, setConfig] = useState<MirroringConfigResponse | null>(null);

  // Fetch robot accounts and teams
  const {robots} = useFetchRobotAccounts(namespace);
  const {teams} = useFetchTeams(namespace);

  // Create dropdown options
  const robotOptions = [
    <React.Fragment key="dropdown-options">
      <SelectOption
        key="create-team"
        component="button"
        onClick={() => setIsCreateTeamModalOpen(true)}
      >
        <UsersIcon /> &nbsp; Create team
      </SelectOption>
      <SelectOption
        key="create-robot"
        component="button"
        onClick={() => setIsCreateRobotModalOpen(true)}
      >
        <DesktopIcon /> &nbsp; Create robot account
      </SelectOption>
      <Divider component="li" key="divider" />
      <SelectGroup label="Teams" key="teams">
        {teams?.map(({name}) => (
          <SelectOption
            key={name}
            value={name}
            onClick={() => {
              const teamEntity: Entity = {
                name,
                is_robot: false,
                kind: EntityKind.team,
                is_org_member: true,
              };
              setSelectedRobot(teamEntity);
              setValue('robotUsername', name);
            }}
          >
            {name}
          </SelectOption>
        ))}
      </SelectGroup>
      <SelectGroup label="Robot accounts" key="robot-accounts">
        {robots?.map(({name}) => (
          <SelectOption
            key={name}
            value={name}
            onClick={() => {
              const robotEntity: Entity = {
                name,
                is_robot: true,
                kind: EntityKind.user,
                is_org_member: true,
              };
              setSelectedRobot(robotEntity);
              setValue('robotUsername', name);
            }}
          >
            {name}
          </SelectOption>
        ))}
      </SelectGroup>
    </React.Fragment>,
  ];

  // Load existing configuration
  useEffect(() => {
    const fetchConfig = async () => {
      try {
        setIsLoading(true);
        const response = await getMirrorConfig(namespace, repoName);
        setConfig(response);

        // Populate form with existing values
        const {value, unit} = convertFromSeconds(response.sync_interval);

        reset({
          isEnabled: response.is_enabled,
          externalReference: response.external_reference || '',
          tags: response.root_rule.rule_value.join(', '),
          syncStartDate: formatDateForInput(response.sync_start_date || ''),
          syncValue: value.toString(),
          syncUnit: unit,
          robotUsername: response.robot_username || '',
          username: response.external_registry_username || '',
          password: '', // Don't populate password for security
          verifyTls: response.external_registry_config?.verify_tls ?? true,
          httpProxy: response.external_registry_config?.proxy?.http_proxy || '',
          httpsProxy:
            response.external_registry_config?.proxy?.https_proxy || '',
          noProxy: response.external_registry_config?.proxy?.no_proxy || '',
          unsignedImages:
            response.external_registry_config?.unsigned_images ?? false,
        });

        // Set selected robot if there's one configured
        if (response.robot_username) {
          const robotEntity: Entity = {
            name: response.robot_username,
            is_robot: response.robot_username.includes('+'),
            kind: response.robot_username.includes('+')
              ? EntityKind.user
              : EntityKind.team,
            is_org_member: true,
          };
          setSelectedRobot(robotEntity);
        }
      } catch (error: unknown) {
        if (
          (error as {response?: {status?: number}}).response?.status === 404
        ) {
          setConfig(null);
        } else {
          setError(
            (error as Error).message || 'Failed to load mirror configuration',
          );
        }
      } finally {
        setIsLoading(false);
      }
    };

    if (repoDetails?.state === 'MIRROR') {
      fetchConfig();
    } else {
      setIsLoading(false);
    }
  }, [namespace, repoName, repoDetails?.state, reset]);

  // Form submission
  const onSubmit = async (data: MirroringFormData) => {
    try {
      // Split and clean up tags to match backend expectation
      const tagPatterns = data.tags
        .split(',')
        .map((tag) => tag.trim())
        .filter((tag) => tag.length > 0);

      const mirrorConfig = {
        is_enabled: data.isEnabled,
        external_reference: data.externalReference,
        external_registry_username: data.username || null,
        external_registry_password: data.password || null,
        sync_start_date: timestampToISO(timestampFromISO(data.syncStartDate)),
        sync_interval: convertToSeconds(Number(data.syncValue), data.syncUnit),
        robot_username: data.robotUsername,
        external_registry_config: {
          verify_tls: data.verifyTls,
          unsigned_images: data.unsignedImages,
          proxy: {
            http_proxy: data.httpProxy || null,
            https_proxy: data.httpsProxy || null,
            no_proxy: data.noProxy || null,
          },
        },
        root_rule: {
          rule_kind: 'tag_glob_csv',
          rule_value: tagPatterns,
        },
      };

      if (config) {
        await updateMirrorConfig(namespace, repoName, mirrorConfig);
      } else {
        await createMirrorConfig(namespace, repoName, mirrorConfig);
      }

      // Reset form with current values to mark it as clean
      reset(data);

      addAlert({
        variant: AlertVariant.Success,
        title: 'Mirror configuration saved successfully',
      });
    } catch (err) {
      setError(err.message);
      addAlert({
        variant: AlertVariant.Failure,
        title: 'Error saving mirror configuration',
        message: err.message,
      });
    }
  };

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
        setErr={setError}
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

  if (isLoading) {
    return <Spinner size="md" />;
  }

  if (error) {
    return <FormError message={error} setErr={setError} />;
  }

  return (
    <div className="pf-v5-u-max-width-lg pf-v5-u-p-md">
      <Form
        isWidthLimited
        data-testid="mirror-form"
        onSubmit={handleSubmit(onSubmit)}
      >
        <MirroringHeader
          namespace={namespace}
          repoName={repoName}
          isConfigured={!!config}
        />
        <Divider className="pf-v5-u-mt-sm" />
        <MirroringConfiguration
          control={control}
          errors={errors}
          formValues={formValues}
          config={config}
          namespace={namespace}
          repoName={repoName}
          selectedRobot={selectedRobot}
          setSelectedRobot={setSelectedRobot}
          isSelectOpen={isSelectOpen}
          setIsSelectOpen={setIsSelectOpen}
          isHovered={isHovered}
          setIsHovered={setIsHovered}
          robotOptions={robotOptions}
          setConfig={setConfig}
          addAlert={addAlert}
        />

        <MirroringCredentials
          control={control}
          errors={errors}
          config={config}
        />

        <MirroringAdvancedSettings
          control={control}
          errors={errors}
          config={config}
        />

        <MirroringStatus
          config={config}
          namespace={namespace}
          repoName={repoName}
          setConfig={setConfig}
          addAlert={addAlert}
        />

        <ActionGroup>
          <Button
            variant={ButtonVariant.primary}
            className="pf-v5-u-display-block pf-v5-u-mx-auto"
            type="submit"
            isDisabled={
              !isValid ||
              !isDirty ||
              !formValues.externalReference ||
              !formValues.tags ||
              !formValues.syncStartDate ||
              !formValues.syncValue ||
              !formValues.robotUsername
            }
            data-testid="submit-button"
          >
            {config ? 'Update Mirror' : 'Enable Mirror'}
          </Button>
        </ActionGroup>

        {/* Robot Creation Modal */}
        <CreateRobotAccountModal
          isModalOpen={isCreateRobotModalOpen}
          handleModalToggle={() => setIsCreateRobotModalOpen(false)}
          orgName={namespace}
          teams={teams}
          RepoPermissionDropdownItems={RepoPermissionDropdownItems}
          setEntity={(robot: Entity) => {
            setSelectedRobot(robot);
            setValue('robotUsername', robot.name);
          }}
          showSuccessAlert={(msg) =>
            addAlert({variant: AlertVariant.Success, title: msg})
          }
          showErrorAlert={(msg) =>
            addAlert({variant: AlertVariant.Failure, title: msg})
          }
        />

        {/* Team Creation Modal */}
        <CreateTeamModal
          teamName={teamName}
          setTeamName={setTeamName}
          description={teamDescription}
          setDescription={setTeamDescription}
          orgName={namespace}
          nameLabel="Provide a name for your new team:"
          descriptionLabel="Provide an optional description for your new team"
          helperText="Enter a description to provide extra information to your teammates about this team:"
          nameHelperText="Choose a name to inform your teammates about this team. Must match ^([a-z0-9]+(?:[._-][a-z0-9]+)*)$"
          isModalOpen={isCreateTeamModalOpen}
          handleModalToggle={() => setIsCreateTeamModalOpen(false)}
          validateName={validateTeamName}
          setAppliedTo={(team: Entity) => {
            setSelectedRobot(team);
            setValue('robotUsername', team.name);
          }}
        />
      </Form>
    </div>
  );
};
