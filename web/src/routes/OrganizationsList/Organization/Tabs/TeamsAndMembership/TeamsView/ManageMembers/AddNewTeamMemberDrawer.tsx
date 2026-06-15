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
  TextInput,
  Split,
  SplitItem,
} from '@patternfly/react-core';
import {DesktopIcon} from '@patternfly/react-icons';
import React, {useState} from 'react';
import {Ref} from 'react';
import {useParams} from 'react-router-dom';
import {AlertVariant, useUI} from 'src/contexts/UIContext';
import EntitySearch from 'src/components/EntitySearch';
import Conditional from 'src/components/empty/Conditional';
import CreateRobotAccountModal from 'src/components/modals/CreateRobotAccountModal';
import {
  useAddMembersToTeam,
  useInviteTeamMemberByEmail,
  useFetchTeamMembersForOrg,
} from 'src/hooks/UseMembers';
import {useFetchTeams} from 'src/hooks/UseTeams';
import {useFetchRobotAccounts} from 'src/hooks/useRobotAccounts';
import {useQuayConfig} from 'src/hooks/UseQuayConfig';
import {Entity} from 'src/resources/UserResource';
import {OrganizationDrawerContentType} from 'src/routes/OrganizationsList/Organization/Organization';
import {RepoPermissionDropdownItems} from 'src/routes/RepositoriesList/RobotAccountsList';

export default function AddNewTeamMemberDrawer(
  props: AddNewTeamMemberDrawerProps,
) {
  const [selectedEntity, setSelectedEntity] = useState<Entity>(null);
  const [isCreateRobotModalOpen, setIsCreateRobotModalOpen] = useState(false);
  const [error, setError] = useState<string>('');
  const [emailInput, setEmailInput] = useState<string>('');
  const {teamName} = useParams();

  // Fetch team sync info to determine if team is in read-only mode
  const {teamSyncInfo} = useFetchTeamMembersForOrg(props.orgName, teamName);
  const pageInReadOnlyMode =
    teamSyncInfo !== null && teamSyncInfo !== undefined;

  // Get robots
  const {robots, isLoadingRobots} = useFetchRobotAccounts(props.orgName);
  // Get teams
  const {teams} = useFetchTeams(props.orgName);
  const quayConfig = useQuayConfig();
  const robotsDisallowed = quayConfig?.config?.ROBOTS_DISALLOW === true;
  const {addAlert} = useUI();

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
      {!robotsDisallowed && (
        <>
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
        </>
      )}
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

  const {inviteMemberByEmail} = useInviteTeamMemberByEmail(props.orgName);

  const addTeamMemberHandler = async () => {
    await addMemberToTeam({
      team: teamName,
      member: selectedEntity.name,
    });
  };

  const isValidEmail = (value: string) =>
    /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value);

  const inviteByEmailHandler = () => {
    const email = emailInput;
    inviteMemberByEmail(
      {team: teamName, email},
      {
        onSuccess: () => {
          addAlert({
            variant: AlertVariant.Success,
            title: `E-mail address ${email} was invited to join the team`,
          });
          setEmailInput('');
          props.closeDrawer();
        },
        onError: () => {
          addAlert({
            variant: AlertVariant.Failure,
            title: `Unable to invite "${email}" to team`,
          });
        },
      },
    );
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
            <FormGroup
              fieldId="creator"
              label="Add a registered user or robot"
              isRequired
            >
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
          <Conditional
            if={quayConfig?.features?.MAILING && !pageInReadOnlyMode}
          >
            <Divider style={{marginTop: '1rem', marginBottom: '1rem'}} />
            <Form id="invite-by-email-form">
              <FormGroup
                fieldId="email-invite"
                label="Or invite by email address"
              >
                <Split hasGutter>
                  <SplitItem isFilled>
                    <TextInput
                      id="email-invite-input"
                      data-testid="email-invite-input"
                      type="email"
                      value={emailInput}
                      onChange={(_event, value) => setEmailInput(value)}
                      placeholder="Enter an email address to invite"
                    />
                  </SplitItem>
                  <SplitItem>
                    <Button
                      data-testid="invite-by-email-btn"
                      isDisabled={!isValidEmail(emailInput)}
                      onClick={inviteByEmailHandler}
                      variant="secondary"
                    >
                      Invite
                    </Button>
                  </SplitItem>
                </Split>
              </FormGroup>
            </Form>
          </Conditional>
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
