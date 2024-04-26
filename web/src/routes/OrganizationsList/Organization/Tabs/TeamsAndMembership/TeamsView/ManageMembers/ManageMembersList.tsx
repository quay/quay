import {
  Button,
  Title,
  Flex,
  PageSection,
  PageSectionVariants,
  Spinner,
  TextArea,
  ToggleGroup,
  ToggleGroupItem,
  ToggleGroupItemProps,
  Toolbar,
  ToolbarContent,
  ToolbarItem,
  FlexItem,
  TextContent,
  TextVariants,
  Text,
  ButtonVariant,
  Divider,
  Tooltip,
  Alert,
  Accordion,
  AccordionItem,
  AccordionContent,
  AccordionToggle,
  TextList,
  TextListVariants,
  TextListItem,
  TextListItemVariants,
} from '@patternfly/react-core';
import {useEffect, useState} from 'react';
import ManageMembersToolbar from './ManageMembersToolbar';
import {Table, Tbody, Td, Th, Thead, Tr} from '@patternfly/react-table';
import './css/ManageMembers.css';
import {
  ITeamMember,
  useDeleteTeamMember,
  useFetchTeamMembersForOrg,
} from 'src/hooks/UseMembers';
import {
  CubesIcon,
  PencilAltIcon,
  TimesIcon,
  CheckIcon,
  TrashIcon,
} from '@patternfly/react-icons';
import {useParams} from 'react-router-dom';
import Empty from 'src/components/empty/Empty';
import {useAlerts} from 'src/hooks/UseAlerts';
import {AlertVariant} from 'src/atoms/AlertState';
import {getAccountTypeForMember} from 'src/libs/utils';
import {OrganizationDrawerContentType} from 'src/routes/OrganizationsList/Organization/Organization';
import {useFetchTeams, useUpdateTeamDetails} from 'src/hooks/UseTeams';
import DeleteModalForRowTemplate from 'src/components/modals/DeleteModalForRowTemplate';
import Conditional from 'src/components/empty/Conditional';
import {useQuayConfig} from 'src/hooks/UseQuayConfig';
import {useOrganization} from 'src/hooks/UseOrganization';
import {useTeamSync, useRemoveTeamSync} from 'src/hooks/UseTeamSync';
import OIDCTeamSyncModal from 'src/components/modals/OIDCTeamSyncModal';
import {ConfirmationModal} from 'src/components/modals/ConfirmationModal';

export enum TableModeType {
  AllMembers = 'All Members',
  TeamMember = 'Team Member',
  RobotAccounts = 'Robot Accounts',
  Invited = 'Invited',
}

export const manageMemberColumnNames = {
  teamMember: 'Team member',
  account: 'Account',
};

interface IMemberInfo {
  teamName: string;
  memberName: string;
}

export default function ManageMembersList(props: ManageMembersListProps) {
  const {organizationName, teamName} = useParams();
  const config = useQuayConfig();
  const {organization} = useOrganization(organizationName);

  const {
    allMembers,
    teamMembers,
    robotAccounts,
    invited,
    paginatedAllMembers,
    paginatedTeamMembers,
    paginatedRobotAccounts,
    paginatedInvited,
    teamCanSync,
    teamSyncInfo,
    loading,
    page,
    setPage,
    perPage,
    setPerPage,
    search,
    setSearch,
  } = useFetchTeamMembersForOrg(organizationName, teamName);

  const {teams} = useFetchTeams(organizationName);

  const [tableMembersList, setTableMembersList] = useState<ITeamMember[]>([]);
  const [allMembersList, setAllMembersList] = useState<ITeamMember[]>([]);
  const [selectedTeamMembers, setSelectedTeamMembers] = useState<ITeamMember[]>(
    [],
  );
  const [tableMode, setTableMode] = useState<TableModeType>(
    TableModeType.AllMembers,
  );
  const {addAlert} = useAlerts();

  const [isEditing, setIsEditing] = useState(false);
  const [teamDescr, setTeamDescr] = useState<string>();
  const [isDeleteModalForRowOpen, setIsDeleteModalForRowOpen] = useState(false);
  const [memberToBeDeleted, setMemberToBeDeleted] = useState<IMemberInfo>();

  // Team Sync states
  const [isOIDCTeamSyncModalOpen, setIsOIDCTeamSyncModalOpen] = useState(false);
  const [OIDCGroupName, setOIDCGroupName] = useState<string>('');
  const [teamSyncLastUpdated, setTeamSyncLastUpdated] =
    useState<string>('Never');
  const [pageInReadOnlyMode, setPageInReadOnlyMode] = useState<boolean>(false);
  const [isRemoveTeamSyncModalOpen, setRemoveTeamSyncModalOpen] =
    useState<boolean>(false);
  const [teamSyncConfigExpanded, setTeamSyncConfigExpanded] = useState(true);

  useEffect(() => {
    switch (tableMode) {
      case TableModeType.AllMembers:
        setTableMembersList(paginatedAllMembers);
        setAllMembersList(allMembers);
        break;

      case TableModeType.TeamMember:
        setTableMembersList(paginatedTeamMembers);
        setAllMembersList(teamMembers);
        break;

      case TableModeType.RobotAccounts:
        setTableMembersList(paginatedRobotAccounts);
        setAllMembersList(robotAccounts);
        break;

      case TableModeType.Invited:
        setTableMembersList(paginatedInvited);
        setAllMembersList(invited);
        break;

      default:
        break;
    }
  }, [tableMode, allMembers, search]);

  const onTableModeChange: ToggleGroupItemProps['onChange'] = (event) => {
    const id = event.currentTarget.id;
    setTableMode(id);
  };

  const onSelectTeamMember = (
    teamMember: ITeamMember,
    rowIndex: number,
    isSelecting: boolean,
  ) => {
    setSelectedTeamMembers((prevSelected) => {
      const otherSelectedTeamMembers = prevSelected.filter(
        (t) => t.name !== teamMember.name,
      );
      return isSelecting
        ? [...otherSelectedTeamMembers, teamMember]
        : otherSelectedTeamMembers;
    });
  };

  const {removeTeamMember, errorDeleteTeamMember, successDeleteTeamMember} =
    useDeleteTeamMember(organizationName);

  useEffect(() => {
    if (successDeleteTeamMember) {
      setIsDeleteModalForRowOpen(false);
      addAlert({
        variant: AlertVariant.Success,
        title: `Successfully deleted team member: ${memberToBeDeleted.memberName}`,
      });
    }
  }, [successDeleteTeamMember]);

  useEffect(() => {
    if (errorDeleteTeamMember) {
      addAlert({
        variant: AlertVariant.Failure,
        title: `Error deleting team member:  ${memberToBeDeleted.memberName}`,
      });
    }
  }, [errorDeleteTeamMember]);

  const deleteRowModal = (
    <DeleteModalForRowTemplate
      deleteMsgTitle={'Remove member from team'}
      isModalOpen={isDeleteModalForRowOpen}
      toggleModal={() => setIsDeleteModalForRowOpen(!isDeleteModalForRowOpen)}
      deleteHandler={removeTeamMember}
      itemToBeDeleted={memberToBeDeleted}
      keyToDisplay="memberName"
    />
  );

  const viewToggle = (
    <Toolbar>
      <ToolbarContent>
        <ToolbarItem spacer={{default: 'spacerMd'}}>
          <ToggleGroup aria-label="Manage members toggle view">
            <ToggleGroupItem
              text="All members"
              buttonId={TableModeType.AllMembers}
              data-testid={TableModeType.AllMembers}
              isSelected={tableMode == TableModeType.AllMembers}
              onChange={onTableModeChange}
            />
            <ToggleGroupItem
              text="Team member"
              buttonId={TableModeType.TeamMember}
              data-testid={TableModeType.TeamMember}
              isSelected={tableMode == TableModeType.TeamMember}
              onChange={onTableModeChange}
              isDisabled={!organization.is_admin}
            />
            <ToggleGroupItem
              text="Robot accounts"
              buttonId={TableModeType.RobotAccounts}
              data-testid={TableModeType.RobotAccounts}
              isSelected={tableMode == TableModeType.RobotAccounts}
              onChange={onTableModeChange}
              isDisabled={!organization.is_admin}
            />
            <ToggleGroupItem
              text="Invited"
              buttonId={TableModeType.Invited}
              data-testid={TableModeType.Invited}
              isSelected={tableMode == TableModeType.Invited}
              onChange={onTableModeChange}
              isDisabled={!organization.is_admin || teamSyncInfo !== undefined}
            />
          </ToggleGroup>
        </ToolbarItem>
      </ToolbarContent>
    </Toolbar>
  );

  const {updateTeamDetails, errorUpdateTeamDetails, successUpdateTeamDetails} =
    useUpdateTeamDetails(organizationName);

  const {enableTeamSync} = useTeamSync({
    orgName: organizationName,
    teamName: teamName,
    onSuccess: (response) => {
      setIsOIDCTeamSyncModalOpen(false);
      setPageInReadOnlyMode(true);
      addAlert({
        variant: AlertVariant.Success,
        title: response,
      });
    },
    onError: (err) => {
      addAlert({
        variant: AlertVariant.Failure,
        title: err,
      });
    },
  });

  const {removeTeamSync} = useRemoveTeamSync({
    orgName: organizationName,
    teamName: teamName,
    onSuccess: (response) => {
      setRemoveTeamSyncModalOpen(false);
      setPageInReadOnlyMode(false);
      addAlert({
        variant: AlertVariant.Success,
        title: response,
      });
    },
    onError: (err) => {
      addAlert({
        variant: AlertVariant.Failure,
        title: err,
      });
    },
  });

  const onAccordionToggle = () => {
    setTeamSyncConfigExpanded(!teamSyncConfigExpanded);
  };

  useEffect(() => {
    if (successUpdateTeamDetails) {
      addAlert({
        variant: AlertVariant.Success,
        title: `Successfully updated team:${teamName} description`,
      });
    }
  }, [successUpdateTeamDetails]);

  useEffect(() => {
    if (errorUpdateTeamDetails) {
      addAlert({
        variant: AlertVariant.Failure,
        title: `Error updating team:${teamName} description`,
      });
    }
  }, [errorUpdateTeamDetails]);

  useEffect(() => {
    if (teamSyncInfo != null) {
      if (teamSyncInfo.service == 'oidc') {
        setOIDCGroupName(teamSyncInfo.config?.group_name);
      }
      if (teamSyncInfo.last_updated != null) {
        setTeamSyncLastUpdated(teamSyncInfo.last_updated);
      }
      setPageInReadOnlyMode(true);
    }
  }, [teamSyncInfo]);

  const updateTeamDescriptionHandler = () => {
    setIsEditing(!isEditing);
    const matchingTeam = teams.find((team) => team.name === teamName);
    updateTeamDetails({
      teamName: teamName,
      teamRole: matchingTeam.role,
      teamDescription: teamDescr,
    });
    setIsEditing(false);
  };

  const getTeamDescription = () => {
    const matchingTeam = teams?.find((team) => team.name === teamName);
    if (matchingTeam) {
      return matchingTeam.description;
    }
  };

  const displayDeleteIcon = (teamAccountType) => {
    if (pageInReadOnlyMode) {
      if (teamAccountType == 'Robot account') {
        return true;
      }
      return false;
    }
    return true;
  };

  const teamDescriptionComponent = (
    <ToolbarContent className="team-description-padding">
      <Flex>
        <FlexItem spacer={{default: 'spacerNone'}}>
          <Title data-testid="teamname-title" headingLevel="h3">
            {teamName}
          </Title>
        </FlexItem>
        <Conditional
          if={config?.registry_state !== 'readonly' && organization.is_admin}
        >
          <Tooltip content={<div>Edit team description</div>}>
            <Button
              variant={'plain'}
              onClick={() => {
                setIsEditing(true);
                setTeamDescr(getTeamDescription());
              }}
              icon={<PencilAltIcon />}
              data-testid="edit-team-description-btn"
            />
          </Tooltip>
        </Conditional>
      </Flex>
      {!isEditing ? (
        <Flex className="text-area-section">
          <FlexItem>
            <TextContent isVisited={false}>
              <Text
                component={TextVariants.p}
                style={{color: 'grey'}}
                data-testid="team-description-text"
              >
                {getTeamDescription()}
              </Text>
            </TextContent>
          </FlexItem>
        </Flex>
      ) : (
        <>
          <TextArea
            value={teamDescr}
            onChange={(_event, value) => setTeamDescr(value)}
            aria-label="team-description"
            data-testid="team-description-text-area"
          />
          <Button
            variant={ButtonVariant.link}
            onClick={updateTeamDescriptionHandler}
            icon={<CheckIcon />}
            data-testid="save-team-description-btn"
          />
          <Button
            variant={'plain'}
            onClick={() => setIsEditing(false)}
            icon={<TimesIcon />}
          />
        </>
      )}
      <Divider />
    </ToolbarContent>
  );

  if (loading) {
    return <Spinner />;
  }

  const removeTeamSyncModalHolder = (
    <ConfirmationModal
      title="Remove Synchronization"
      description="Are you sure you want to disable group syncing on this team? The team will once again become editable."
      buttonText="Confirm"
      modalOpen={isRemoveTeamSyncModalOpen}
      toggleModal={() => setRemoveTeamSyncModalOpen(!isRemoveTeamSyncModalOpen)}
      handleModalConfirm={() => removeTeamSync()}
    />
  );

  const displaySyncDirectory =
    teamCanSync != null &&
    !teamSyncInfo &&
    config?.registry_state !== 'readonly';

  const fetchSyncBtn = () => {
    const result = [];
    if (displaySyncDirectory) {
      result.push(
        <Button
          variant="link"
          onClick={() => setIsOIDCTeamSyncModalOpen(!isOIDCTeamSyncModalOpen)}
          key="team-sync-btn"
        >
          Enable Team Sync
        </Button>,
      );
    }
    if (pageInReadOnlyMode && teamCanSync) {
      result.push(
        <Button
          onClick={() => setRemoveTeamSyncModalOpen(!isRemoveTeamSyncModalOpen)}
          key="remove-team-sync-btn"
        >
          Remove synchronization
        </Button>,
      );
    }
    return result;
  };

  const teamSyncedConfig = (
    <>
      <Alert
        isInline
        variant="info"
        title={`This team is synchronized with a group in ${teamSyncInfo?.service} and its user membership is therefore read-only.`}
        id="teamsync-readonly-alert"
      />
      <Conditional if={OIDCGroupName != null}>
        <Accordion>
          <AccordionItem>
            <AccordionToggle
              onClick={() => onAccordionToggle()}
              isExpanded={!teamSyncConfigExpanded}
              id="team-sync-config-toggle"
            >
              Team Synchronization Config
            </AccordionToggle>
            <AccordionContent
              id="team-sync-config-toggle"
              isHidden={!teamSyncConfigExpanded}
            >
              <TextContent>
                <TextList component={TextListVariants.dl}>
                  <TextListItem component={TextListItemVariants.dt}>
                    Bound to group
                  </TextListItem>
                  <TextListItem component={TextListItemVariants.dd}>
                    {OIDCGroupName}
                  </TextListItem>
                  <TextListItem component={TextListItemVariants.dt}>
                    Last Updated
                  </TextListItem>
                  <TextListItem component={TextListItemVariants.dd}>
                    {teamSyncLastUpdated}
                  </TextListItem>
                </TextList>
              </TextContent>
            </AccordionContent>
          </AccordionItem>
        </Accordion>
      </Conditional>
    </>
  );

  const OIDCTeamSyncModalHolder = (
    <OIDCTeamSyncModal
      isModalOpen={isOIDCTeamSyncModalOpen}
      toggleModal={() => setIsOIDCTeamSyncModalOpen(!isOIDCTeamSyncModalOpen)}
      titleText="Enable OIDC Team Sync"
      primaryText="Team synchronization allows this team's user membership to be backed by a group in OIDC."
      onConfirmSync={(groupName) =>
        enableTeamSync(groupName, teamCanSync?.service)
      }
      secondaryText={`Enter the group ${
        teamCanSync?.issuer_domain?.includes('microsoft') ? `Object Id` : `name`
      } you'd like to sync membership with:`}
      alertText={`Please note that once team syncing is enabled, the membership of users who are already part of the team will be revoked. OIDC group will be the single source of truth. This is a non-reversible action. Team's user membership from within ${config?.config.REGISTRY_TITLE_SHORT} will be read-only.`}
    />
  );

  if (allMembers?.length === 0) {
    return (
      <>
        <Conditional if={pageInReadOnlyMode}>{teamSyncedConfig}</Conditional>
        <Empty
          title="There are no viewable members for this team"
          icon={CubesIcon}
          body="Either no team members exist yet or you may not have permission to view any."
          button={
            <Conditional
              if={
                config?.registry_state !== 'readonly' &&
                organization.is_admin &&
                !pageInReadOnlyMode
              }
            >
              <Button
                variant="primary"
                data-testid="add-new-member-button"
                onClick={() =>
                  props.setDrawerContent(
                    OrganizationDrawerContentType.AddNewTeamMemberDrawer,
                  )
                }
              >
                Add new member
              </Button>
            </Conditional>
          }
          secondaryActions={fetchSyncBtn()}
        />
        <Conditional if={isOIDCTeamSyncModalOpen}>
          {OIDCTeamSyncModalHolder}
        </Conditional>
        <Conditional if={isRemoveTeamSyncModalOpen && teamCanSync != null}>
          {removeTeamSyncModalHolder}
        </Conditional>
      </>
    );
  }

  return (
    <>
      <Conditional if={pageInReadOnlyMode}>{teamSyncedConfig}</Conditional>
      <PageSection variant={PageSectionVariants.light}>
        <ManageMembersToolbar
          selectedTeams={selectedTeamMembers}
          deSelectAll={() => setSelectedTeamMembers([])}
          allItems={allMembersList}
          paginatedItems={tableMembersList}
          onItemSelect={onSelectTeamMember}
          page={page}
          setPage={setPage}
          perPage={perPage}
          setPerPage={setPerPage}
          search={search}
          setSearch={setSearch}
          searchOptions={[manageMemberColumnNames.teamMember]}
          setDrawerContent={props.setDrawerContent}
          isReadOnly={config?.registry_state === 'readonly'}
          isAdmin={organization.is_admin}
          displaySyncDirectory={displaySyncDirectory}
          isOIDCTeamSyncModalOpen={isOIDCTeamSyncModalOpen}
          toggleOIDCTeamSyncModal={() =>
            setIsOIDCTeamSyncModalOpen(!isOIDCTeamSyncModalOpen)
          }
          teamCanSync={teamCanSync}
          pageInReadOnlyMode={pageInReadOnlyMode}
          isRemoveTeamSyncModalOpen={isRemoveTeamSyncModalOpen}
          toggleRemoveTeamSyncModal={() =>
            setRemoveTeamSyncModalOpen(!isRemoveTeamSyncModalOpen)
          }
        >
          {viewToggle}
          {teamDescriptionComponent}
          <Conditional if={isDeleteModalForRowOpen}>
            {deleteRowModal}
          </Conditional>
          <Conditional
            if={isOIDCTeamSyncModalOpen && teamCanSync?.service == 'oidc'}
          >
            {OIDCTeamSyncModalHolder}
          </Conditional>
          <Conditional if={isRemoveTeamSyncModalOpen && teamCanSync != null}>
            {removeTeamSyncModalHolder}
          </Conditional>
          <Table aria-label="Selectable table" variant="compact">
            <Thead>
              <Tr>
                <Th />
                <Th>{manageMemberColumnNames.teamMember}</Th>
                <Th>{manageMemberColumnNames.account}</Th>
                <Th />
              </Tr>
            </Thead>
            <Tbody>
              {tableMembersList?.map((teamMember, rowIndex) => (
                <Tr key={rowIndex}>
                  <Td
                    select={{
                      rowIndex,
                      onSelect: (_event, isSelecting) =>
                        onSelectTeamMember(teamMember, rowIndex, isSelecting),
                      isSelected: selectedTeamMembers.some(
                        (t) => t.name === teamMember.name,
                      ),
                    }}
                  />
                  <Td
                    dataLabel={manageMemberColumnNames.teamMember}
                    data-testid={teamMember.name}
                  >
                    {teamMember.name}
                  </Td>
                  <Td dataLabel={manageMemberColumnNames.account}>
                    {getAccountTypeForMember(teamMember)}
                  </Td>
                  <Conditional
                    if={
                      config?.registry_state !== 'readonly' &&
                      organization.is_admin &&
                      displayDeleteIcon(getAccountTypeForMember(teamMember))
                    }
                  >
                    <Td>
                      <Button
                        icon={<TrashIcon />}
                        variant="plain"
                        onClick={() => {
                          setMemberToBeDeleted({
                            teamName: teamName,
                            memberName: teamMember.name,
                          });
                          setIsDeleteModalForRowOpen(!isDeleteModalForRowOpen);
                        }}
                        data-testid={`${teamMember.name}-delete-icon`}
                      />
                    </Td>
                  </Conditional>
                </Tr>
              ))}
            </Tbody>
          </Table>
        </ManageMembersToolbar>
      </PageSection>
    </>
  );
}
interface ManageMembersListProps {
  setDrawerContent?: (contentType: OrganizationDrawerContentType) => void;
}
