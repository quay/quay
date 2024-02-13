import {
  Alert,
  Button,
  Divider,
  SelectGroup,
  SelectOption,
  Spinner,
  AlertVariant as PFAlertVariant,
  HelperText,
  HelperTextItem,
} from '@patternfly/react-core';
import {DesktopIcon} from '@patternfly/react-icons';
import React from 'react';
import {useState} from 'react';
import {AlertVariant} from 'src/atoms/AlertState';
import EntitySearch from 'src/components/EntitySearch';
import FileUpload from 'src/components/FileUpload';
import Conditional from 'src/components/empty/Conditional';
import CreateRobotAccountModal from 'src/components/modals/CreateRobotAccountModal';
import {useAlerts} from 'src/hooks/UseAlerts';
import {useStartDockerfileBuild} from 'src/hooks/UseBuilds';
import {useQuayConfig} from 'src/hooks/UseQuayConfig';
import {useRepository, useTransitivePermissions} from 'src/hooks/UseRepository';
import {useFetchTeams} from 'src/hooks/UseTeams';
import {useRobotAccounts} from 'src/hooks/useRobotAccounts';
import {getRegistryBaseImage} from 'src/libs/dockerfileParser';
import {isNullOrUndefined} from 'src/libs/utils';
import {RepositoryBuild} from 'src/resources/BuildResource';
import {Entity} from 'src/resources/UserResource';
import {RepoPermissionDropdownItems} from 'src/routes/RepositoriesList/RobotAccountsList';

export default function DockerfileUploadBuild(
  props: DockerfileUploadBuildProps,
) {
  const [rejected, setRejected] = useState<boolean>(false);
  const [value, setValue] = useState('');
  const [privateRepo, setPrivatRepo] = useState<string>();
  const [selectedRobot, setSelectedRobot] = useState<string>(null);
  const [isCreateRobotModalOpen, setIsCreateRobotModalOpen] = useState(false);
  const {addAlert} = useAlerts();
  const {teams} = useFetchTeams(props.org);
  const [org, repo] = privateRepo?.split('/') ?? [null, null];
  const {repoDetails} = useRepository(org, repo);
  const {
    permissions,
    isLoading: isLoadingTransitivePermissions,
    isError: isErrorLoadingTransitivePermissions,
    error: errorLoadingTransitivePermissions,
  } = useTransitivePermissions(props.org, props.repo, selectedRobot);
  const {
    robotAccountsForOrg: robots,
    loading,
    isError,
    error,
  } = useRobotAccounts({
    name: props.org,
    onSuccess: () => null,
    onError: () => null,
    enabled: !isNullOrUndefined(privateRepo),
  });
  const {startBuild} = useStartDockerfileBuild(props.org, props.repo, {
    onSuccess: (data: RepositoryBuild) => {
      addAlert({
        variant: AlertVariant.Success,
        title: `Build started with ID ${data.id}`,
      });
      props.onClose();
    },
    onError: (error) => {
      addAlert({
        variant: AlertVariant.Failure,
        title: `Failed to start build`,
      });
    },
  });
  const config = useQuayConfig();

  if (isErrorLoadingTransitivePermissions) {
    return (
      <Alert
        variant={PFAlertVariant.danger}
        title="Failed to verify robot account permissions"
      />
    );
  }
  if (isError) {
    return (
      <Alert
        variant={PFAlertVariant.danger}
        title="Failed to load robot accounts for private base image"
      />
    );
  }

  const onFileUpload = (value: string) => {
    if (value.includes('FROM')) {
      const baseImage = getRegistryBaseImage(
        value,
        config?.config?.SERVER_HOSTNAME,
      );
      if (!isNullOrUndefined(baseImage)) {
        setPrivatRepo(baseImage);
      }
      setValue(value);
      setRejected(false);
    } else {
      setRejected(true);
      setValue('');
    }
  };
  return (
    <>
      <FileUpload
        id="dockerfile-upload"
        value={value}
        onValueChange={onFileUpload}
        onClear={() => {
          setValue('');
          setPrivatRepo(null);
          setSelectedRobot(null);
          setRejected(false);
        }}
      />
      <Conditional if={rejected}>
        <HelperText>
          <HelperTextItem variant={rejected ? 'error' : 'default'}>
            Invalid Dockerfile format
          </HelperTextItem>
        </HelperText>
      </Conditional>
      <p>Please select a Dockerfile</p>
      <Conditional
        if={
          !isNullOrUndefined(privateRepo) &&
          !isNullOrUndefined(repoDetails) &&
          !repoDetails.is_public
        }
      >
        <br />
        <Alert
          variant={PFAlertVariant.warning}
          title={
            <>
              <p>
                The selected Dockerfile contains a <code>FROM</code> that refers
                to private repository <strong>{privateRepo}</strong>.
              </p>
              <p>
                A robot account with read access to that repository is required
                for the build:
              </p>
            </>
          }
        />
        <br />
        <EntitySearch
          id="repository-creator-dropdown"
          org={props.org}
          includeTeams={false}
          onSelect={(e: Entity) => {
            setSelectedRobot(e.name);
          }}
          onClear={() => setSelectedRobot(null)}
          value={selectedRobot}
          defaultOptions={
            <React.Fragment key="creator">
              <SelectGroup label="Robot accounts" key="robot-account-grp">
                {loading ? (
                  <Spinner />
                ) : (
                  robots?.map(({name}) => (
                    <SelectOption
                      data-testid={`${name}-robot-accnt`}
                      key={name}
                      value={name}
                      onClick={() => {
                        setSelectedRobot(name);
                      }}
                    >
                      {name}
                    </SelectOption>
                  ))
                )}
              </SelectGroup>
              <Divider component="li" key={7} />
              <SelectOption
                data-testid="create-new-robot-accnt-btn"
                key="create-robot-account"
                component="button"
                onClick={() =>
                  setIsCreateRobotModalOpen(!isCreateRobotModalOpen)
                }
                isFocused
              >
                <DesktopIcon /> &nbsp; Create robot account
              </SelectOption>
            </React.Fragment>
          }
          placeholderText="Add a registered user, robot to team"
        />
        <Conditional
          if={
            !isNullOrUndefined(selectedRobot) &&
            permissions?.length === 0 &&
            !isLoadingTransitivePermissions
          }
        >
          <br />
          <Alert
            variant={PFAlertVariant.warning}
            title={
              <>
                Robot account <strong>{selectedRobot}</strong> does not have
                read permission on repository <strong>{privateRepo}</strong>
              </>
            }
          />
        </Conditional>
      </Conditional>
      <br />
      <br />
      <Button
        isDisabled={
          isNullOrUndefined(value) ||
          value === '' ||
          (isNullOrUndefined(selectedRobot) &&
            !isNullOrUndefined(privateRepo) &&
            !isNullOrUndefined(repoDetails) &&
            !repoDetails.is_public)
        }
        onClick={() =>
          startBuild({dockerfileContent: value, robot: selectedRobot})
        }
      >
        Start Build
      </Button>{' '}
      <Button onClick={() => props.onClose()}>Close</Button>
      <Conditional if={isCreateRobotModalOpen}>
        <CreateRobotAccountModal
          isModalOpen={isCreateRobotModalOpen}
          handleModalToggle={() =>
            setIsCreateRobotModalOpen(!isCreateRobotModalOpen)
          }
          orgName={props.org}
          teams={teams}
          RepoPermissionDropdownItems={RepoPermissionDropdownItems}
          setEntity={(entity: Entity) => setSelectedRobot(entity.name)}
          showSuccessAlert={(message) =>
            addAlert({
              variant: AlertVariant.Success,
              title: message,
            })
          }
          showErrorAlert={(message) =>
            addAlert({
              variant: AlertVariant.Failure,
              title: message,
            })
          }
        />
      </Conditional>
    </>
  );
}

interface DockerfileUploadBuildProps {
  org: string;
  repo: string;
  onClose: () => void;
}
