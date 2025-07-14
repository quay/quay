import React, {useState, useEffect} from 'react';
import {useForm, Controller} from 'react-hook-form';
import {
  Form,
  FormGroup,
  TextInput,
  Checkbox,
  Button,
  ButtonVariant,
  ActionGroup,
  Divider,
  Text,
  TextContent,
  Title,
  InputGroup,
  Select,
  SelectOption,
  SelectGroup,
  MenuToggle,
  Spinner,
  ValidatedOptions,
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
import EntitySearch from 'src/components/EntitySearch';
import {Entity, EntityKind} from 'src/resources/UserResource';
import {RepoPermissionDropdownItems} from 'src/routes/RepositoriesList/RobotAccountsList';
import {
  MirroringConfigResponse,
  getMirrorConfig,
  createMirrorConfig,
  updateMirrorConfig,
  toggleMirroring,
  syncMirror,
  cancelSync,
  timestampToISO,
  timestampFromISO,
  statusLabels,
} from 'src/resources/MirroringResource';
import './Mirroring.css';

interface MirroringProps {
  namespace: string;
  repoName: string;
}

// Form data type that matches the existing state structure
interface MirroringFormData {
  isEnabled: boolean;
  externalReference: string;
  tags: string;
  syncStartDate: string;
  syncValue: string;
  syncUnit: string;
  robotUsername: string;
  username: string;
  password: string;
  verifyTls: boolean;
  httpProxy: string;
  httpsProxy: string;
  noProxy: string;
  unsignedImages: boolean;
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

  // Non-form UI state (same as before)
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

  // Fetch robot accounts and teams (same as before)
  const {robots} = useFetchRobotAccounts(namespace);
  const {teams} = useFetchTeams(namespace);

  // Unit conversion utilities (same as before)
  const timeUnits = {
    seconds: 1,
    minutes: 60,
    hours: 60 * 60,
    days: 60 * 60 * 24,
    weeks: 60 * 60 * 24 * 7,
  };

  const convertToSeconds = (value: number, unit: string): number => {
    return value * (timeUnits[unit] || 1);
  };

  const convertFromSeconds = (
    seconds: number,
  ): {value: number; unit: string} => {
    const units = ['weeks', 'days', 'hours', 'minutes', 'seconds'];
    for (const unit of units) {
      const divisor = timeUnits[unit];
      if (seconds % divisor === 0) {
        return {value: seconds / divisor, unit};
      }
    }
    return {value: seconds, unit: 'seconds'};
  };

  // Convert ISO date to datetime-local format
  const formatDateForInput = (isoDate: string): string => {
    if (!isoDate) return '';
    try {
      const date = new Date(isoDate);
      // Format as YYYY-MM-DDTHH:MM (datetime-local format)
      return date.toISOString().slice(0, 16);
    } catch (error) {
      console.error('Error formatting date:', error);
      return '';
    }
  };

  // Validation functions (same logic as before)
  const validateRequired = (value: string) => {
    if (!value || value.trim() === '') {
      return 'This field is required';
    }
    return true;
  };

  const validateSyncValue = (value: string) => {
    if (!value || value.trim() === '') {
      return 'This field is required';
    }
    const numValue = Number(value);
    if (isNaN(numValue) || numValue <= 0) {
      return 'Must be a positive number';
    }
    return true;
  };

  // Team validation function (same as before)
  const validateTeamName = (name: string): boolean => {
    return /^([a-z0-9]+(?:[._-][a-z0-9]+)*)$/.test(name);
  };

  // Create dropdown options (same as before)
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

  // Load existing configuration (same as before)
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

  // Form submission (same logic as before)
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

  // Helper function to get validation state for PatternFly
  const getValidationState = (
    fieldName: keyof MirroringFormData,
  ): ValidatedOptions => {
    return errors[fieldName]
      ? ValidatedOptions.error
      : ValidatedOptions.default;
  };

  // Early returns (same as before)
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
      <TextContent>
        <Title headingLevel="h2">Repository Mirroring</Title>
      </TextContent>
      <Form
        isWidthLimited
        data-testid="mirror-form"
        onSubmit={handleSubmit(onSubmit)}
      >
        <TextContent>
          {config ? (
            <Text>
              This repository is configured as a mirror. While enabled, Quay
              will periodically replicate any matching images on the external
              registry. Users cannot manually push to this repository.
            </Text>
          ) : (
            <Text>
              This feature will convert{' '}
              <strong>
                {namespace}/{repoName}
              </strong>{' '}
              into a mirror. Changes to the external repository will be
              duplicated here. While enabled, users will be unable to push
              images to this repository.
            </Text>
          )}
        </TextContent>
        <Divider className="pf-v5-u-mt-sm" />
        <Title headingLevel="h3">
          {config ? 'Configuration' : 'External Repository'}
        </Title>
        {config && (
          <FormGroup fieldId="is_enabled" isStack>
            <Controller
              name="isEnabled"
              control={control}
              render={({field: {value, onChange}}) => (
                <Checkbox
                  label="Enabled"
                  id="is_enabled"
                  name="is_enabled"
                  description={
                    value
                      ? 'Scheduled mirroring enabled. Immediate sync available via Sync Now.'
                      : 'Scheduled mirroring disabled. Immediate sync available via Sync Now.'
                  }
                  isChecked={value}
                  data-testid="mirror-enabled-checkbox"
                  onChange={async (_event, checked) => {
                    try {
                      await toggleMirroring(namespace, repoName, checked);
                      onChange(checked);
                      addAlert({
                        variant: AlertVariant.Success,
                        title: `Mirror ${
                          checked ? 'enabled' : 'disabled'
                        } successfully`,
                      });
                    } catch (err) {
                      addAlert({
                        variant: AlertVariant.Failure,
                        title: 'Error toggling mirror',
                        message: err.message,
                      });
                    }
                  }}
                />
              )}
            />
          </FormGroup>
        )}

        <FormGroup
          label="Registry Location"
          fieldId="external_reference"
          isStack
        >
          <Controller
            name="externalReference"
            control={control}
            rules={{validate: validateRequired}}
            render={({field: {value, onChange}}) => (
              <TextInput
                type="text"
                id="external_reference"
                name="external_reference"
                placeholder="quay.io/redhat/quay"
                value={value}
                onChange={(_event, newValue) => onChange(newValue)}
                validated={getValidationState('externalReference')}
                data-testid="registry-location-input"
              />
            )}
          />
        </FormGroup>

        <FormGroup label="Tags" fieldId="tags" isStack>
          <Text component="small" className="pf-v5-c-form__helper-text">
            Comma-separated list of tag patterns to synchronize.
          </Text>
          <Controller
            name="tags"
            control={control}
            rules={{validate: validateRequired}}
            render={({field: {value, onChange}}) => (
              <TextInput
                type="text"
                id="tags"
                name="tags"
                placeholder="Examples: latest, 3.3*, *"
                value={value}
                onChange={(_event, newValue) => onChange(newValue)}
                validated={getValidationState('tags')}
                data-testid="tags-input"
              />
            )}
          />
        </FormGroup>

        <FormGroup
          label={config ? 'Next Sync Date' : 'Start Date'}
          fieldId="sync_start_date"
          isStack
        >
          {config ? (
            <div style={{display: 'flex', alignItems: 'center', gap: '8px'}}>
              <Controller
                name="syncStartDate"
                control={control}
                rules={{validate: validateRequired}}
                render={({field: {value, onChange}}) => (
                  <TextInput
                    type="datetime-local"
                    id="sync_start_date"
                    name="sync_start_date"
                    value={value}
                    onChange={(_event, newValue) => onChange(newValue)}
                    validated={getValidationState('syncStartDate')}
                    style={{flex: 1}}
                  />
                )}
              />
              <Button
                variant="primary"
                size="sm"
                type="button"
                isDisabled={
                  config.sync_status === 'SYNCING' ||
                  config.sync_status === 'SYNC_NOW'
                }
                data-testid="sync-now-button"
                onClick={async () => {
                  try {
                    await syncMirror(namespace, repoName);
                    addAlert({
                      variant: AlertVariant.Success,
                      title: 'Sync scheduled successfully',
                    });
                    const response = await getMirrorConfig(namespace, repoName);
                    setConfig(response);
                  } catch (err) {
                    addAlert({
                      variant: AlertVariant.Failure,
                      title: 'Error scheduling sync',
                      message: err.message,
                    });
                  }
                }}
              >
                Sync Now
              </Button>
            </div>
          ) : (
            <Controller
              name="syncStartDate"
              control={control}
              rules={{validate: validateRequired}}
              render={({field: {value, onChange}}) => (
                <TextInput
                  type="datetime-local"
                  id="sync_start_date"
                  name="sync_start_date"
                  value={value}
                  onChange={(_event, newValue) => onChange(newValue)}
                  validated={getValidationState('syncStartDate')}
                />
              )}
            />
          )}
        </FormGroup>

        <FormGroup label="Sync Interval" fieldId="sync_interval" isStack>
          <InputGroup
            onPointerEnterCapture={() => setIsHovered(true)}
            onPointerLeaveCapture={() => setIsHovered(false)}
            className={isHovered ? 'pf-v5-u-background-color-200' : ''}
          >
            <Controller
              name="syncValue"
              control={control}
              rules={{validate: validateSyncValue}}
              render={({field: {value, onChange}}) => (
                <TextInput
                  type="text"
                  id="sync_interval"
                  name="sync_interval"
                  value={value}
                  onChange={(_event, newValue) => {
                    const numericValue = newValue.replace(/[^0-9]/g, '');
                    onChange(numericValue);
                  }}
                  pattern="[0-9]*"
                  inputMode="numeric"
                  validated={getValidationState('syncValue')}
                  aria-label="Sync interval value"
                  data-testid="sync-interval-input"
                />
              )}
            />
            <Controller
              name="syncUnit"
              control={control}
              render={({field: {value, onChange}}) => (
                <Select
                  isOpen={isSelectOpen}
                  onOpenChange={(isOpen) => setIsSelectOpen(isOpen)}
                  onSelect={(_event, selectedValue) => {
                    onChange(selectedValue as string);
                    setIsSelectOpen(false);
                  }}
                  selected={value}
                  aria-label="Sync interval unit"
                  toggle={(toggleRef) => (
                    <MenuToggle
                      ref={toggleRef}
                      onClick={() => setIsSelectOpen(!isSelectOpen)}
                      isExpanded={isSelectOpen}
                    >
                      {value}
                    </MenuToggle>
                  )}
                >
                  <SelectOption value="seconds">seconds</SelectOption>
                  <SelectOption value="minutes">minutes</SelectOption>
                  <SelectOption value="hours">hours</SelectOption>
                  <SelectOption value="days">days</SelectOption>
                  <SelectOption value="weeks">weeks</SelectOption>
                </Select>
              )}
            />
          </InputGroup>
        </FormGroup>

        <FormGroup label="Robot User" fieldId="robot_username" isStack>
          <Controller
            name="robotUsername"
            control={control}
            rules={{validate: validateRequired}}
            render={() => (
              <EntitySearch
                id="robot-user-select"
                org={namespace}
                includeTeams={true}
                onSelect={(robot: Entity) => {
                  setSelectedRobot(robot);
                  setValue('robotUsername', robot.name);
                }}
                onClear={() => {
                  setSelectedRobot(null);
                  setValue('robotUsername', '');
                }}
                value={selectedRobot?.name}
                onError={() =>
                  addAlert({
                    variant: AlertVariant.Failure,
                    title: 'Error loading robot users',
                    message: 'Failed to load available robots',
                  })
                }
                defaultOptions={robotOptions}
                placeholderText="Select a team or user..."
                data-testid="robot-user-select"
              />
            )}
          />
        </FormGroup>

        <Divider />
        <Title headingLevel="h3">Credentials</Title>
        <Text
          component="small"
          className="pf-v5-c-form__helper-text pf-v5-u-text-align-center pf-v5-u-display-block"
        >
          Required if the external repository is private.
        </Text>

        <FormGroup label="Username" fieldId="username" isStack>
          <Controller
            name="username"
            control={control}
            render={({field: {value, onChange}}) => (
              <TextInput
                type="text"
                id="username"
                name="username"
                value={value}
                onChange={(_event, newValue) => onChange(newValue)}
                validated={getValidationState('username')}
                data-testid="username-input"
              />
            )}
          />
        </FormGroup>

        <FormGroup
          label="Password"
          fieldId="external_registry_password"
          isStack
        >
          <Controller
            name="password"
            control={control}
            render={({field: {value, onChange}}) => (
              <TextInput
                type="password"
                id="external_registry_password"
                name="external_registry_password"
                value={value}
                onChange={(_event, newValue) => onChange(newValue)}
                validated={getValidationState('password')}
                data-testid="password-input"
              />
            )}
          />
        </FormGroup>

        <Divider />
        <Title headingLevel="h3">Advanced Settings</Title>

        <FormGroup fieldId="verify_tls" isStack>
          <Controller
            name="verifyTls"
            control={control}
            render={({field: {value, onChange}}) => (
              <Checkbox
                label="Verify TLS"
                id="verify_tls"
                name="verify_tls"
                description="Require HTTPS and verify certificates when talking to the external registry."
                isChecked={value}
                onChange={(_event, checked) => onChange(checked)}
                data-testid="verify-tls-checkbox"
              />
            )}
          />
        </FormGroup>

        <FormGroup fieldId="unsigned_images" isStack>
          <Controller
            name="unsignedImages"
            control={control}
            render={({field: {value, onChange}}) => (
              <Checkbox
                label="Accept Unsigned Images"
                id="unsigned_images"
                name="unsigned_images"
                description="Allow unsigned images to be mirrored."
                isChecked={value}
                onChange={(_event, checked) => onChange(checked)}
                data-testid="unsigned-images-checkbox"
              />
            )}
          />
        </FormGroup>

        <FormGroup label="HTTP Proxy" fieldId="http_proxy" isStack>
          <Controller
            name="httpProxy"
            control={control}
            render={({field: {value, onChange}}) => (
              <TextInput
                type="text"
                id="http_proxy"
                name="http_proxy"
                placeholder="proxy.example.com"
                value={value ?? 'None'}
                onChange={(_event, newValue) =>
                  onChange(newValue === 'None' ? null : newValue)
                }
                data-testid="http-proxy-input"
              />
            )}
          />
        </FormGroup>

        <FormGroup label="HTTPs Proxy" fieldId="https_proxy" isStack>
          <Controller
            name="httpsProxy"
            control={control}
            render={({field: {value, onChange}}) => (
              <TextInput
                type="text"
                id="https_proxy"
                name="https_proxy"
                placeholder="proxy.example.com"
                value={value ?? 'None'}
                onChange={(_event, newValue) =>
                  onChange(newValue === 'None' ? null : newValue)
                }
                data-testid="https-proxy-input"
              />
            )}
          />
        </FormGroup>

        <FormGroup label="No Proxy" fieldId="no_proxy" isStack>
          <Controller
            name="noProxy"
            control={control}
            render={({field: {value, onChange}}) => (
              <TextInput
                type="text"
                id="no_proxy"
                name="no_proxy"
                placeholder="example.com"
                value={value ?? 'None'}
                onChange={(_event, newValue) =>
                  onChange(newValue === 'None' ? null : newValue)
                }
                data-testid="no-proxy-input"
              />
            )}
          />
        </FormGroup>

        {/* Status section for configured mirrors */}
        {config && (
          <>
            <Divider />
            <Title headingLevel="h3">Status</Title>
            <div className="pf-v5-u-max-width-lg pf-v5-u-mx-auto">
              <div className="pf-v5-l-flex pf-v5-l-flex--align-items-center pf-v5-u-mb-sm">
                <div className="pf-v5-l-flex__item pf-v5-m-flex-1">
                  <strong>State</strong>{' '}
                  <span className="pf-v5-u-ml-sm">
                    {statusLabels[config.sync_status] || config.sync_status}
                  </span>
                </div>
                <Button
                  variant="danger"
                  size="sm"
                  type="button"
                  isDisabled={
                    config.sync_status !== 'SYNCING' &&
                    config.sync_status !== 'SYNC_NOW'
                  }
                  className="pf-v5-u-ml-md"
                  data-testid="cancel-sync-button"
                  onClick={async () => {
                    try {
                      await cancelSync(namespace, repoName);
                      addAlert({
                        variant: AlertVariant.Success,
                        title: 'Sync cancelled successfully',
                      });
                      const response = await getMirrorConfig(
                        namespace,
                        repoName,
                      );
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
              </div>
              <div className="pf-v5-u-mb-sm">
                <strong>Timeout</strong>{' '}
                <span className="pf-v5-u-ml-sm">
                  {config.sync_expiration_date
                    ? config.sync_expiration_date
                    : 'None'}
                </span>
              </div>
              <div>
                <strong>Retries Remaining</strong>{' '}
                <span className="pf-v5-u-ml-sm">
                  {config.sync_retries_remaining != null
                    ? `${config.sync_retries_remaining} / 3`
                    : '3 / 3'}
                </span>
              </div>
            </div>
          </>
        )}

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
