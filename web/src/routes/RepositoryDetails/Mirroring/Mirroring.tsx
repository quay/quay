import React, {useState, useEffect} from 'react';
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

// Using PatternFly's ValidatedOptions enum instead of custom type

export const Mirroring: React.FC<MirroringProps> = ({namespace, repoName}) => {
  const {
    repoDetails,
    errorLoadingRepoDetails,
    isLoading: isLoadingRepo,
  } = useRepository(namespace, repoName);
  const {addAlert} = useAlerts();

  // Form state
  const [isEnabled, setIsEnabled] = useState(true);
  const [externalReference, setExternalReference] = useState('');
  const [tags, setTags] = useState('');
  const [syncStartDate, setSyncStartDate] = useState('');
  const [syncValue, setSyncValue] = useState('');
  const [syncUnit, setSyncUnit] = useState('minutes');
  const [robotUsername, setRobotUsername] = useState('');
  const [selectedRobot, setSelectedRobot] = useState<Entity | null>(null);
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [verifyTls, setVerifyTls] = useState(true);
  const [httpProxy, setHttpProxy] = useState('');
  const [httpsProxy, setHttpsProxy] = useState('');
  const [noProxy, setNoProxy] = useState('');
  const [unsignedImages, setUnsignedImages] = useState(false);

  // UI state
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

  // Validation state
  const [validated, setValidated] = useState<Record<string, ValidatedOptions>>(
    {},
  );

  // Fetch robot accounts for the dropdown
  const {robots} = useFetchRobotAccounts(namespace);

  // Fetch teams for the dropdown
  const {teams} = useFetchTeams(namespace);

  // Unit conversion utilities
  const timeUnits = {
    seconds: 1,
    minutes: 60,
    hours: 60 * 60,
    days: 60 * 60 * 24,
    weeks: 60 * 60 * 24 * 7,
  };

  // Convert display value + unit to seconds for backend
  const convertToSeconds = (value: number, unit: string): number => {
    return value * (timeUnits[unit] || 1);
  };

  // Convert seconds from backend to best display unit + value
  const convertFromSeconds = (
    seconds: number,
  ): {value: number; unit: string} => {
    // Find the largest unit that divides evenly into the seconds
    const units = ['weeks', 'days', 'hours', 'minutes', 'seconds'];
    for (const unit of units) {
      const divisor = timeUnits[unit];
      if (seconds % divisor === 0) {
        return {value: seconds / divisor, unit};
      }
    }
    // Fallback to seconds if no clean division
    return {value: seconds, unit: 'seconds'};
  };

  // Create options for the dropdown (creation options first, then teams and robots)
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
              setRobotUsername(name);
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
              setRobotUsername(name);
            }}
          >
            {name}
          </SelectOption>
        ))}
      </SelectGroup>
    </React.Fragment>,
  ];

  // Team validation function
  const validateTeamName = (name: string): boolean => {
    return /^([a-z0-9]+(?:[._-][a-z0-9]+)*)$/.test(name);
  };

  useEffect(() => {
    const fetchConfig = async () => {
      try {
        const response = await getMirrorConfig(namespace, repoName);
        setConfig(response);

        // Update form state from response
        setIsEnabled(response.is_enabled);
        setExternalReference(response.external_reference);
        setTags(
          Array.isArray(response.root_rule.rule_value)
            ? response.root_rule.rule_value.join(', ')
            : response.root_rule.rule_value,
        );
        setSyncStartDate(
          response.sync_start_date.replace('Z', '').slice(0, 16),
        );
        const {value, unit} = convertFromSeconds(response.sync_interval);
        setSyncValue(value.toString());
        setSyncUnit(unit);
        setRobotUsername(response.robot_username);
        // Set selected robot based on the robot username
        if (response.robot_username) {
          setSelectedRobot({
            name: response.robot_username,
            is_robot: true,
            kind: EntityKind.user,
            is_org_member: true,
          });
        }
        setUsername(response.external_registry_username);
        setPassword(''); // Password is not returned from the API for security reasons
        setVerifyTls(response.external_registry_config.verify_tls);
        setUnsignedImages(
          response.external_registry_config.unsigned_images ?? false,
        );
        setHttpProxy(response.external_registry_config.proxy.http_proxy);
        setHttpsProxy(response.external_registry_config.proxy.https_proxy);
        setNoProxy(response.external_registry_config.proxy.no_proxy);
      } catch (err) {
        // If the error is a 404, it means no mirror config exists yet
        if (err.response?.status === 404) {
          console.info(
            'No repository mirror configuration (404). This is expected for a new mirror setup.',
            err,
          );
          setConfig(null);
          // Set default values for a new mirror configuration
          setIsEnabled(true);
          setExternalReference('');
          setTags('');
          // Get current date/time in local timezone for datetime-local input
          const now = new Date();
          const localDateTime = new Date(
            now.getTime() - now.getTimezoneOffset() * 60000,
          )
            .toISOString()
            .slice(0, 16);
          setSyncStartDate(localDateTime);
          setSyncValue('');
          setSyncUnit('seconds');
          setRobotUsername('');
          setSelectedRobot(null);
          setUsername('');
          setPassword('');
          setVerifyTls(false);
          setUnsignedImages(false);
          setHttpProxy('');
          setHttpsProxy('');
          setNoProxy('');
        } else {
          addAlert({
            variant: AlertVariant.Failure,
            title: 'Error loading mirror configuration',
            message: err.message,
          });
          setError(err.message);
        }
      } finally {
        setIsLoading(false);
      }
    };

    if (repoDetails) {
      if (repoDetails.state === 'MIRROR') {
        fetchConfig();
      } else {
        setIsLoading(false);
      }
    } else if (!isLoadingRepo) {
      // If we're not loading repo details and we don't have them, something went wrong
      setIsLoading(false);
    }
  }, [namespace, repoName, repoDetails, isLoadingRepo]);

  const validateField = (
    name: string,
    value: string | number | undefined,
  ): ValidatedOptions => {
    if (!value) return ValidatedOptions.error;
    return ValidatedOptions.success;
  };

  const validateForm = (): boolean => {
    const newValidated = {
      externalReference: validateField('externalReference', externalReference),
      tags: validateField('tags', tags),
      syncStartDate: validateField('syncStartDate', syncStartDate),
      syncValue: validateField('syncValue', syncValue),
      robotUsername: validateField('robotUsername', robotUsername),
    };

    setValidated(newValidated);
    return Object.values(newValidated).every(
      (v) => v === ValidatedOptions.success,
    );
  };

  // Check if required fields are filled without side effects
  const isFormValid = () => {
    const isValidSyncValue =
      syncValue.trim() !== '' &&
      !isNaN(Number(syncValue)) &&
      Number(syncValue) > 0;
    return !!(
      externalReference &&
      tags &&
      syncStartDate &&
      isValidSyncValue &&
      robotUsername
    );
  };

  const handleSubmit = async () => {
    if (!validateForm()) {
      return;
    }

    try {
      // Split and clean up tags to match backend expectation
      const tagPatterns = tags
        .split(',')
        .map((tag) => tag.trim())
        .filter((tag) => tag.length > 0);

      const mirrorConfig = {
        is_enabled: isEnabled,
        external_reference: externalReference,
        external_registry_username: username || null,
        external_registry_password: password || null,
        sync_start_date: timestampToISO(timestampFromISO(syncStartDate)),
        sync_interval: convertToSeconds(Number(syncValue), syncUnit),
        robot_username: robotUsername,
        external_registry_config: {
          verify_tls: verifyTls,
          unsigned_images: unsignedImages,
          proxy: {
            http_proxy: httpProxy || null,
            https_proxy: httpsProxy || null,
            no_proxy: noProxy || null,
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
      <TextContent>
        <Title headingLevel="h2">Repository Mirroring</Title>
      </TextContent>
      <Form isWidthLimited data-testid="mirror-form">
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
            <Checkbox
              label="Enabled"
              id="is_enabled"
              name="is_enabled"
              description={
                isEnabled
                  ? 'Scheduled mirroring enabled. Immediate sync available via Sync Now.'
                  : 'Scheduled mirroring disabled. Immediate sync available via Sync Now.'
              }
              isChecked={isEnabled}
              data-testid="mirror-enabled-checkbox"
              onChange={async (_event, checked) => {
                try {
                  await toggleMirroring(namespace, repoName, checked);

                  // Update only the local state, don't update config to avoid conflicts
                  // Use the checked parameter since backend is working but response.is_enabled is undefined
                  setIsEnabled(checked);

                  // Note: We're not updating setConfig here to avoid potential race conditions
                  // The config will be refreshed on next useEffect if needed

                  addAlert({
                    variant: AlertVariant.Success,
                    title: `Mirror ${
                      checked ? 'enabled' : 'disabled'
                    } successfully`,
                  });
                } catch (err) {
                  addAlert({
                    variant: AlertVariant.Failure,
                    title: 'Error updating mirror status',
                    message: err.message,
                  });
                }
              }}
            />
          </FormGroup>
        )}
        <FormGroup
          label="Registry Location"
          fieldId="external_reference"
          isStack
        >
          <TextInput
            type="text"
            id="external_reference"
            name="external_reference"
            placeholder="quay.io/redhat/quay"
            value={externalReference}
            onChange={(_event, value) => setExternalReference(value)}
            validated={validated.externalReference}
            data-testid="registry-location-input"
          />
        </FormGroup>

        <FormGroup label="Tags" fieldId="tags" isStack>
          <Text component="small" className="pf-v5-c-form__helper-text">
            Comma-separated list of tag patterns to synchronize.
          </Text>
          <TextInput
            type="text"
            id="tags"
            name="tags"
            placeholder="Examples: latest, 3.3*, *"
            value={tags}
            onChange={(_event, value) => setTags(value)}
            validated={validated.tags}
            data-testid="tags-input"
          />
        </FormGroup>

        <FormGroup
          label={config ? 'Next Sync Date' : 'Start Date'}
          fieldId="sync_start_date"
          isStack
        >
          {config ? (
            // For configured mirrors: show date with Sync Now button
            <div style={{display: 'flex', alignItems: 'center', gap: '8px'}}>
              <TextInput
                type="datetime-local"
                id="sync_start_date"
                name="sync_start_date"
                value={syncStartDate}
                onChange={(_event, value) => setSyncStartDate(value)}
                validated={validated.syncStartDate}
                style={{flex: 1}}
              />
              <Button
                variant="primary"
                size="sm"
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
                    // Refresh the config to get updated status
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
            // For new mirrors: just the date input
            <TextInput
              type="datetime-local"
              id="sync_start_date"
              name="sync_start_date"
              value={syncStartDate}
              onChange={(_event, value) => setSyncStartDate(value)}
              validated={validated.syncStartDate}
            />
          )}
        </FormGroup>
        <FormGroup label="Sync Interval" fieldId="sync_interval" isStack>
          <InputGroup
            onPointerEnterCapture={() => setIsHovered(true)}
            onPointerLeaveCapture={() => setIsHovered(false)}
            className={isHovered ? 'pf-v5-u-background-color-200' : ''}
          >
            <TextInput
              type="text"
              id="sync_interval"
              name="sync_interval"
              value={syncValue}
              onChange={(_event, value) => {
                // Only allow digits
                const numericValue = value.replace(/[^0-9]/g, '');
                setSyncValue(numericValue);
              }}
              pattern="[0-9]*"
              inputMode="numeric"
              validated={validated.syncValue}
              aria-label="Sync interval value"
              data-testid="sync-interval-input"
            />
            <Select
              isOpen={isSelectOpen}
              onOpenChange={(isOpen) => setIsSelectOpen(isOpen)}
              onSelect={(_event, value) => {
                setSyncUnit(value as string);
                setIsSelectOpen(false);
              }}
              selected={syncUnit}
              aria-label="Sync interval unit"
              toggle={(toggleRef) => (
                <MenuToggle
                  ref={toggleRef}
                  onClick={() => setIsSelectOpen(!isSelectOpen)}
                  isExpanded={isSelectOpen}
                >
                  {syncUnit}
                </MenuToggle>
              )}
            >
              <SelectOption value="seconds">seconds</SelectOption>
              <SelectOption value="minutes">minutes</SelectOption>
              <SelectOption value="hours">hours</SelectOption>
              <SelectOption value="days">days</SelectOption>
              <SelectOption value="weeks">weeks</SelectOption>
            </Select>
          </InputGroup>
        </FormGroup>

        <FormGroup label="Robot User" fieldId="robot_username" isStack>
          <EntitySearch
            id="robot-user-select"
            org={namespace}
            includeTeams={true}
            onSelect={(robot: Entity) => {
              setSelectedRobot(robot);
              setRobotUsername(robot.name);
            }}
            onClear={() => {
              setSelectedRobot(null);
              setRobotUsername('');
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
          <TextInput
            type="text"
            id="username"
            name="username"
            value={username}
            onChange={(_event, value) => setUsername(value)}
            validated={validated.username}
            data-testid="username-input"
          />
        </FormGroup>

        <FormGroup
          label="Password"
          fieldId="external_registry_password"
          isStack
        >
          <TextInput
            type="password"
            id="external_registry_password"
            name="external_registry_password"
            value={password}
            onChange={(_event, value) => setPassword(value)}
            validated={validated.password}
            data-testid="password-input"
          />
        </FormGroup>

        <Divider />
        <Title headingLevel="h3">Advanced Settings</Title>
        <FormGroup fieldId="verify_tls" isStack>
          <Checkbox
            label="Verify TLS"
            id="verify_tls"
            name="verify_tls"
            description="Require HTTPS and verify certificates when talking to the external registry."
            isChecked={verifyTls}
            onChange={(_event, isChecked) => setVerifyTls(isChecked)}
            data-testid="verify-tls-checkbox"
          />
        </FormGroup>

        <FormGroup fieldId="unsigned_images" isStack>
          <Checkbox
            label="Accept Unsigned Images"
            id="unsigned_images"
            name="unsigned_images"
            description="Allow unsigned images to be mirrored."
            isChecked={unsignedImages}
            onChange={(_event, isChecked) => setUnsignedImages(isChecked)}
            data-testid="unsigned-images-checkbox"
          />
        </FormGroup>

        <FormGroup label="HTTP Proxy" fieldId="http_proxy" isStack>
          <TextInput
            type="text"
            id="http_proxy"
            name="http_proxy"
            placeholder="proxy.example.com"
            value={httpProxy ?? 'None'}
            onChange={(_event, value) =>
              setHttpProxy(value === 'None' ? null : value)
            }
            data-testid="http-proxy-input"
          />
        </FormGroup>

        <FormGroup label="HTTPs Proxy" fieldId="https_proxy" isStack>
          <TextInput
            type="text"
            id="https_proxy"
            name="https_proxy"
            placeholder="proxy.example.com"
            value={httpsProxy ?? 'None'}
            onChange={(_event, value) =>
              setHttpsProxy(value === 'None' ? null : value)
            }
            data-testid="https-proxy-input"
          />
        </FormGroup>

        <FormGroup label="No Proxy" fieldId="no_proxy" isStack>
          <TextInput
            type="text"
            id="no_proxy"
            name="no_proxy"
            placeholder="example.com"
            value={noProxy ?? 'None'}
            onChange={(_event, value) =>
              setNoProxy(value === 'None' ? null : value)
            }
            data-testid="no-proxy-input"
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
                      // Refresh the config to get updated status
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
            onClick={handleSubmit}
            isDisabled={!isFormValid()}
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
            setRobotUsername(robot.name);
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
            setRobotUsername(team.name);
          }}
        />
      </Form>
    </div>
  );
};
