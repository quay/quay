import {useState, Ref} from 'react';
import {
  ActionGroup,
  Button,
  Divider,
  DrawerActions,
  DrawerCloseButton,
  DrawerHead,
  DrawerPanelBody,
  DrawerPanelContent,
  Dropdown,
  DropdownItem,
  DropdownList,
  Form,
  FormGroup,
  MenuToggle,
  MenuToggleElement,
  Radio,
  SelectGroup,
  SelectOption,
  Spinner,
} from '@patternfly/react-core';
import {DesktopIcon, UsersIcon} from '@patternfly/react-icons';
import EntitySearch from 'src/components/EntitySearch';
import {useCreateDefaultPermission} from 'src/hooks/UseDefaultPermissions';
import {Entity} from 'src/resources/UserResource';
import React from 'react';
import {useFetchRobotAccounts} from 'src/hooks/useRobotAccounts';
import CreateRobotAccountModal from 'src/components/modals/CreateRobotAccountModal';
import {CreateTeamWizard} from 'src/routes/OrganizationsList/Organization/Tabs/DefaultPermissions/createTeamWizard/CreateTeamWizard';
import {CreateTeamModal} from 'src/routes/OrganizationsList/Organization/Tabs/DefaultPermissions/createPermissionDrawer/CreateTeamModal';
import {OrganizationDrawerContentType} from 'src/routes/OrganizationsList/Organization/Organization';
import Conditional from 'src/components/empty/Conditional';
import {useFetchTeams} from 'src/hooks/UseTeams';
import {repoPermissions} from 'src/routes/OrganizationsList/Organization/Tabs/DefaultPermissions/DefaultPermissionsList';
import {RepoPermissionDropdownItems} from 'src/routes/RepositoriesList/RobotAccountsList';
import {useAlerts} from 'src/hooks/UseAlerts';
import {AlertVariant} from 'src/atoms/AlertState';
import {validateTeamName} from 'src/libs/utils';

export default function CreatePermissionDrawer(
  props: CreatePermissionDrawerProps,
) {
  enum userType {
    ANYONE = 'Anyone',
    SPECIFIC_USER = 'Specific user',
  }

  const [createdBy, setCreatedBy] = useState(userType.SPECIFIC_USER);
  const [repositoryCreator, setRepositoryCreator] = useState<Entity>(null);
  const [appliedTo, setAppliedTo] = useState<Entity>(null);
  const [permission, setPermission] = useState<repoPermissions>(
    repoPermissions.READ,
  );
  const [permissionDropDownOpen, setPermissionDropDownOpen] = useState(false);
  const [error, setError] = useState<string>('');

  const [
    isCreateRobotModalForCreatorOpen,
    setIsCreateRobotModalForCreatorOpen,
  ] = useState(false);
  const [
    isCreateRobotModalForAppliedToOpen,
    setIsCreateRobotModalForAppliedToOpen,
  ] = useState(false);

  // state variables for Create Team
  const [teamName, setTeamName] = useState('');
  const [teamDescription, setTeamDescription] = useState('');
  const [isTeamModalOpen, setIsTeamModalOpen] = useState<boolean>(false);
  const [isTeamWizardOpen, setIsTeamWizardOpen] = useState<boolean>(false);

  // Get robots
  const {robots, isLoadingRobots} = useFetchRobotAccounts(props.orgName);
  // Get teams
  const {teams, isLoadingTeams} = useFetchTeams(props.orgName);
  const {addAlert} = useAlerts();

  const permissionRadioButtons = (
    <>
      <Radio
        data-testid={userType.ANYONE}
        isChecked={createdBy === userType.ANYONE}
        name={userType.ANYONE}
        onChange={() => setCreatedBy(userType.ANYONE)}
        label={userType.ANYONE}
        id={userType.ANYONE}
        value={userType.ANYONE}
      />
      <Radio
        data-testid={userType.SPECIFIC_USER}
        isChecked={createdBy === userType.SPECIFIC_USER}
        name={userType.SPECIFIC_USER}
        onChange={() => setCreatedBy(userType.SPECIFIC_USER)}
        label={userType.SPECIFIC_USER}
        id={userType.SPECIFIC_USER}
        value={userType.SPECIFIC_USER}
      />
    </>
  );

  // TODO: https://www.patternfly.org/v4/components/select#view-more
  const creatorDefaultOptions = [
    <React.Fragment key="creator">
      <SelectGroup label="Robot accounts" key="robot-account-grp">
        {isLoadingRobots ? (
          <Spinner />
        ) : (
          robots?.map(({name}) => (
            <SelectOption
              data-testid={`${name}-robot-accnt`}
              key={name}
              value={name}
              onClick={() => {
                setRepositoryCreator({
                  name,
                  is_robot: true,
                  kind: 'user',
                  is_org_member: true,
                });
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
          setIsCreateRobotModalForCreatorOpen(!isCreateRobotModalForCreatorOpen)
        }
        isFocused
      >
        <DesktopIcon /> &nbsp; Create robot account
      </SelectOption>
    </React.Fragment>,
  ];

  const dropdownForCreator = (
    <EntitySearch
      id="repository-creator-dropdown"
      org={props.orgName}
      includeTeams={false}
      onSelect={(e: Entity) => {
        setRepositoryCreator(e);
      }}
      onClear={() => setRepositoryCreator(null)}
      value={repositoryCreator?.name}
      onError={() => setError('Unable to look up users')}
      defaultOptions={creatorDefaultOptions}
      placeholderText="Search user/robot"
    />
  );

  const createTeamModal = (
    <CreateTeamModal
      teamName={teamName}
      setTeamName={setTeamName}
      description={teamDescription}
      setDescription={setTeamDescription}
      orgName={props.orgName}
      nameLabel="Provide a name for your new team:"
      descriptionLabel="Provide an optional description for your new team"
      helperText="Enter a description to provide extra information to your teammates about this team:"
      nameHelperText="Choose a name to inform your teammates about this team. Must match ^([a-z0-9]+(?:[._-][a-z0-9]+)*)$"
      isModalOpen={isTeamModalOpen}
      handleModalToggle={() => setIsTeamModalOpen(!isTeamModalOpen)}
      handleWizardToggle={() => setIsTeamWizardOpen(!isTeamWizardOpen)}
      validateName={validateTeamName}
      setAppliedTo={setAppliedTo}
    />
  );

  const createTeamWizard = (
    <CreateTeamWizard
      teamName={teamName}
      teamDescription={teamDescription}
      isTeamWizardOpen={isTeamWizardOpen}
      handleWizardToggle={() => setIsTeamWizardOpen(!isTeamWizardOpen)}
      orgName={props.orgName}
    />
  );

  const createRobotModalForRepositoryCreator = (
    <CreateRobotAccountModal
      isModalOpen={isCreateRobotModalForCreatorOpen}
      handleModalToggle={() =>
        setIsCreateRobotModalForCreatorOpen(!isCreateRobotModalForCreatorOpen)
      }
      orgName={props.orgName}
      teams={teams}
      RepoPermissionDropdownItems={RepoPermissionDropdownItems}
      setEntity={setRepositoryCreator}
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
  );

  const createRobotModalForAppliedTo = (
    <CreateRobotAccountModal
      isModalOpen={isCreateRobotModalForAppliedToOpen}
      handleModalToggle={() =>
        setIsCreateRobotModalForAppliedToOpen(
          !isCreateRobotModalForAppliedToOpen,
        )
      }
      orgName={props.orgName}
      teams={teams}
      RepoPermissionDropdownItems={RepoPermissionDropdownItems}
      setEntity={setAppliedTo}
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
  );

  const appliedToDefaultOptions = [
    <React.Fragment key="appliedTo">
      <SelectGroup label="Teams" key="group3">
        {isLoadingTeams ? (
          <Spinner />
        ) : (
          teams?.map(({name}) => (
            <SelectOption
              data-testid={`${name}-team`}
              key={name}
              value={name}
              onClick={() => {
                setAppliedTo({
                  name,
                  is_robot: false,
                  kind: 'team',
                });
              }}
            >
              {name}
            </SelectOption>
          ))
        )}
      </SelectGroup>
      <Divider component="li" key={4} />
      <SelectGroup label="Robot accounts" key="group4">
        {robots?.map(({name}) => {
          return (
            <SelectOption
              data-testid={`${name}-robot-accnt`}
              key={name}
              value={name}
              onClick={() => {
                setAppliedTo({
                  name,
                  is_robot: true,
                  kind: 'user',
                  is_org_member: true,
                });
              }}
            >
              {name}
            </SelectOption>
          );
        })}
      </SelectGroup>
      <Divider component="li" key={5} />
      <SelectOption
        data-testid="create-new-team-btn"
        key="Create team1"
        component="button"
        onClick={() => setIsTeamModalOpen(!isTeamModalOpen)}
        isFocused
      >
        <UsersIcon /> &nbsp; Create team
      </SelectOption>
      <SelectOption
        data-testid="create-new-robot-accnt-btn"
        key="Create robot account2"
        component="button"
        onClick={() =>
          setIsCreateRobotModalForAppliedToOpen(
            !isCreateRobotModalForAppliedToOpen,
          )
        }
        isFocused
      >
        <DesktopIcon /> &nbsp; Create robot account
      </SelectOption>
    </React.Fragment>,
  ];

  const dropdownForAppliedTo = (
    <EntitySearch
      id="applied-to-dropdown"
      org={props.orgName}
      includeTeams={true}
      onSelect={(e: Entity) => {
        setAppliedTo(e);
      }}
      onClear={() => setAppliedTo(null)}
      value={appliedTo?.name}
      onError={() => setError('Unable to look up teams')}
      defaultOptions={appliedToDefaultOptions}
      placeholderText="Search, invite or add user/robot/team"
    />
  );

  const optionsForPermission = Object.keys(repoPermissions).map((key) => (
    <DropdownItem
      data-testid={`repoPermissions-${key}`}
      key={repoPermissions[key]}
      value={repoPermissions[key]}
      onClick={() => {
        setPermission(repoPermissions[key]);
        setPermissionDropDownOpen(!permissionDropDownOpen);
      }}
    >
      {repoPermissions[key]}
    </DropdownItem>
  ));

  const dropdownForPermission = (
    <Dropdown
      data-testid={'create-default-permission-dropdown'}
      toggle={(toggleRef: React.Ref<MenuToggleElement>) => (
        <MenuToggle
          ref={toggleRef}
          onClick={() => setPermissionDropDownOpen(!permissionDropDownOpen)}
          isExpanded={permissionDropDownOpen}
          data-testid="create-default-permission-dropdown-toggle"
        >
          {permission}
        </MenuToggle>
      )}
      isOpen={permissionDropDownOpen}
      onOpenChange={(isOpen) => setPermissionDropDownOpen(isOpen)}
      shouldFocusToggleOnSelect
    >
      <DropdownList>{optionsForPermission}</DropdownList>
    </Dropdown>
  );
  const {createDefaultPermission} = useCreateDefaultPermission(props.orgName, {
    onSuccess: () => {
      addAlert({
        variant: AlertVariant.Success,
        title: repositoryCreator
          ? `Successfully created default permission for creator: ${repositoryCreator.name}`
          : `Successfully applied default permission to: ${appliedTo.name}`,
      });
    },
    onError: () => {
      addAlert({
        variant: AlertVariant.Failure,
        title: repositoryCreator
          ? `Unable to create default permission for creator: ${repositoryCreator.name}`
          : `Unable to apply default permission to: ${appliedTo.name}`,
      });
    },
  });

  const createDefaultPermissionHandler = async () => {
    if (createdBy === userType.SPECIFIC_USER) {
      await createDefaultPermission({
        repoCreator: repositoryCreator,
        appliedTo: appliedTo,
        newRole: permission.toLowerCase(),
      });
    } else if (createdBy === userType.ANYONE) {
      await createDefaultPermission({
        appliedTo: appliedTo,
        newRole: permission.toLowerCase(),
      });
    }
    setTeamName('');
    props.closeDrawer();
  };

  return (
    <>
      <Conditional if={isTeamModalOpen}>{createTeamModal}</Conditional>
      <Conditional if={isTeamWizardOpen}>{createTeamWizard}</Conditional>
      <Conditional if={isCreateRobotModalForCreatorOpen}>
        {createRobotModalForRepositoryCreator}
      </Conditional>
      <Conditional if={isCreateRobotModalForAppliedToOpen}>
        {createRobotModalForAppliedTo}
      </Conditional>
      <DrawerPanelContent>
        <DrawerHead className="pf-v5-c-title pf-m-xl">
          <h6
            tabIndex={
              props.drawerContent != OrganizationDrawerContentType.None ? 0 : -1
            }
            ref={props.drawerRef}
          >
            Create default permission
          </h6>

          <DrawerActions>
            <DrawerCloseButton onClick={props.closeDrawer} />
          </DrawerActions>
        </DrawerHead>
        <DrawerPanelBody>
          <h3 className="pf-v5-c-title pf-m-md">
            Applies when a repository is created by:
          </h3>
        </DrawerPanelBody>
        <DrawerPanelBody>
          <Form id="create-permission-form">
            <FormGroup fieldId="create-by-radio">
              {permissionRadioButtons}
            </FormGroup>
            {createdBy === userType.SPECIFIC_USER ? (
              <FormGroup
                fieldId="creator"
                label="Repository creator"
                isRequired
              >
                {dropdownForCreator}
              </FormGroup>
            ) : null}
            <FormGroup fieldId="applied-to" label="Applied to" isRequired>
              {dropdownForAppliedTo}
            </FormGroup>
            <FormGroup fieldId="permission" label="Permission" isRequired>
              {dropdownForPermission}
            </FormGroup>
            <ActionGroup>
              <Button
                data-testid="create-permission-button"
                isDisabled={
                  ((repositoryCreator === null ||
                    Object.keys(repositoryCreator).length === 0) &&
                    createdBy === userType.SPECIFIC_USER) ||
                  appliedTo === null ||
                  Object.keys(appliedTo).length === 0
                }
                onClick={createDefaultPermissionHandler}
                variant="primary"
              >
                Create default permission
              </Button>
            </ActionGroup>
          </Form>
        </DrawerPanelBody>
      </DrawerPanelContent>
    </>
  );
}

interface CreatePermissionDrawerProps {
  orgName: string;
  closeDrawer: () => void;
  drawerRef: Ref<HTMLDivElement>;
  drawerContent: OrganizationDrawerContentType;
}
