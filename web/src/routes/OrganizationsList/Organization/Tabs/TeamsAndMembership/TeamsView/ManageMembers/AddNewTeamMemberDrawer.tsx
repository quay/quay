import {
  ActionGroup,
  Alert,
  Button,
  Divider,
  DrawerActions,
  DrawerCloseButton,
  DrawerHead,
  DrawerPanelBody,
  DrawerPanelContent,
  Form,
  FormGroup,
  SelectGroup,
  SelectOption,
  Spinner,
} from '@patternfly/react-core';
import {DesktopIcon} from '@patternfly/react-icons';
import React, {useState} from 'react';
import {Ref} from 'react';
import {useParams} from 'react-router-dom';
import {AlertVariant} from 'src/atoms/AlertState';
import EntitySearch from 'src/components/EntitySearch';
import Conditional from 'src/components/empty/Conditional';
import CreateRobotAccountModal from 'src/components/modals/CreateRobotAccountModal';
import {useAlerts} from 'src/hooks/UseAlerts';
import {
  useAddMembersToTeam,
  useFetchTeamMembersForOrg,
} from 'src/hooks/UseMembers';
import {useFetchTeams} from 'src/hooks/UseTeams';
import {useFetchRobotAccounts} from 'src/hooks/useRobotAccounts';
import {Entity} from 'src/resources/UserResource';
import {OrganizationDrawerContentType} from 'src/routes/OrganizationsList/Organization/Organization';
import {RepoPermissionDropdownItems} from 'src/routes/RepositoriesList/RobotAccountsList';

export default function AddNewTeamMemberDrawer(
  props: AddNewTeamMemberDrawerProps,
) {
  const [selectedEntity, setSelectedEntity] = useState<Entity>(null);
  const [isCreateRobotModalOpen, setIsCreateRobotModalOpen] = useState(false);
  const [error, setError] = useState<string>('');
  const {teamName} = useParams();

  // Fetch team sync info to determine if team is in read-only mode
  const {teamSyncInfo} = useFetchTeamMembersForOrg(props.orgName, teamName);
  const pageInReadOnlyMode =
    teamSyncInfo !== null && teamSyncInfo !== undefined;

  // Get robots
  const {robots, isLoadingRobots} = useFetchRobotAccounts(props.orgName);
  // Get teams
  const {teams} = useFetchTeams(props.orgName);
  const {addAlert} = useAlerts();

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
                setSelectedEntity({
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
        onClick={() => setIsCreateRobotModalOpen(!isCreateRobotModalOpen)}
        isFocused
      >
        <DesktopIcon /> &nbsp; Create robot account
      </SelectOption>
    </React.Fragment>,
  ];

  const dropdownForCreator = pageInReadOnlyMode ? (
    <EntitySearch
      id="repository-creator-dropdown"
      org={props.orgName}
      includeTeams={false}
      includeRobots={false}
      isDisabled={true}
      onSelect={(e: Entity) => {
        setSelectedEntity(e);
      }}
      onClear={() => setSelectedEntity(null)}
      value={selectedEntity?.name}
      onError={() => setError('Unable to look up users')}
      defaultOptions={creatorDefaultOptions}
      placeholderText="Select a robot account to add to team"
    />
  ) : (
    <EntitySearch
      id="repository-creator-dropdown"
      org={props.orgName}
      includeTeams={false}
      onSelect={(e: Entity) => {
        setSelectedEntity(e);
      }}
      onClear={() => setSelectedEntity(null)}
      value={selectedEntity?.name}
      onError={() => setError('Unable to look up users')}
      defaultOptions={creatorDefaultOptions}
      placeholderText="Add a registered user, robot to team"
    />
  );

  const createRobotModal = (
    <CreateRobotAccountModal
      isModalOpen={isCreateRobotModalOpen}
      handleModalToggle={() =>
        setIsCreateRobotModalOpen(!isCreateRobotModalOpen)
      }
      orgName={props.orgName}
      teams={teams}
      RepoPermissionDropdownItems={RepoPermissionDropdownItems}
      setEntity={setSelectedEntity}
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

  const {addMemberToTeam} = useAddMembersToTeam(props.orgName, {
    onSuccess: () => {
      addAlert({
        variant: AlertVariant.Success,
        title: `Successfully added "${selectedEntity.name}" to team`,
      });
      props.closeDrawer();
    },
    onError: () => {
      addAlert({
        variant: AlertVariant.Failure,
        title: `Unable to add "${selectedEntity.name}" to team`,
      });
    },
  });

  const addTeamMemberHandler = async () => {
    await addMemberToTeam({
      team: teamName,
      member: selectedEntity.name,
    });
  };

  return (
    <>
      <Conditional if={isCreateRobotModalOpen}>{createRobotModal}</Conditional>
      <DrawerPanelContent>
        <DrawerHead className="pf-c-title pf-m-xl">
          <h6
            tabIndex={
              props.drawerContent != OrganizationDrawerContentType.None ? 0 : -1
            }
            ref={props.drawerRef}
          >
            {pageInReadOnlyMode
              ? 'Add robot account to team'
              : 'Add team member'}
          </h6>
          <DrawerActions>
            <DrawerCloseButton onClick={props.closeDrawer} />
          </DrawerActions>
        </DrawerHead>
        <DrawerPanelBody>
          <Conditional if={pageInReadOnlyMode}>
            <Alert
              isInline
              variant="info"
              title="This team is synchronized with an external directory group"
              style={{marginBottom: '1rem'}}
            >
              User membership is managed by the directory service. Only robot
              accounts can be added to this team.
            </Alert>
          </Conditional>
          <Form id="add-new-member-form">
            <FormGroup fieldId="creator" label="Repository creator" isRequired>
              {dropdownForCreator}
            </FormGroup>
            <ActionGroup>
              <Button
                data-testid="add-new-member-submit-btn"
                isDisabled={
                  selectedEntity === null ||
                  Object.keys(selectedEntity).length === 0
                }
                onClick={addTeamMemberHandler}
                variant="primary"
              >
                Add member
              </Button>
            </ActionGroup>
          </Form>
        </DrawerPanelBody>
      </DrawerPanelContent>
    </>
  );
}

interface AddNewTeamMemberDrawerProps {
  orgName: string;
  closeDrawer: () => void;
  drawerRef: Ref<HTMLDivElement>;
  drawerContent: OrganizationDrawerContentType;
}
