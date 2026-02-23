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
import {useEffect, useState, useMemo} from 'react';
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
import {AlertVariant, useUI} from 'src/contexts/UIContext';
import {
  getAccountTypeForMember,
  formatDate,
  formatRelativeTime,
} from 'src/libs/utils';
import {OrganizationDrawerContentType} from 'src/routes/OrganizationsList/Organization/Organization';
import {useFetchTeams, useUpdateTeamDetails} from 'src/hooks/UseTeams';
import DeleteModalForRowTemplate from 'src/components/modals/DeleteModalForRowTemplate';
import Conditional from 'src/components/empty/Conditional';
import {useQuayConfig} from 'src/hooks/UseQuayConfig';
import {useOrganization} from 'src/hooks/UseOrganization';
import {useTeamSync, useRemoveTeamSync} from 'src/hooks/UseTeamSync';
import DirectoryTeamSyncModal from 'src/components/modals/DirectoryTeamSyncModal';
import {ConfirmationModal} from 'src/components/modals/ConfirmationModal';
import {usePaginatedSortableTable} from '../../../../../../../hooks/usePaginatedSortableTable';
import {SupportedService} from 'src/resources/TeamSyncResource';

function getServiceDisplayName(service: SupportedService): string {
  const serviceNames: Record<SupportedService, string> = {
    ldap: 'LDAP',
    keystone: 'Keystone',
    oidc: 'OIDC',
  };
  return serviceNames[service];
}

function getGroupFieldLabel(
  service: SupportedService,
  issuerDomain?: string,
): string {
  if (service === 'ldap') {
    return 'Group DN';
  } else if (service === 'keystone') {
    return 'Group ID';
  } else if (service === 'oidc') {
    return issuerDomain?.includes('microsoft') ? 'Object Id' : 'Group Name';
  }
  return 'Group Name';
}

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
    teamCanSync,
    teamSyncInfo,
    loading,
    search,
    setSearch,
  } = useFetchTeamMembersForOrg(organizationName, teamName);

  const [tableMode, setTableMode] = useState<TableModeType>(
    TableModeType.AllMembers,
  );

  // Get the appropriate data source based on table mode (memoized for reactivity)
  const currentDataSource = useMemo(() => {
    switch (tableMode) {
      case TableModeType.AllMembers:
        return allMembers || [];
      case TableModeType.TeamMember:
        return teamMembers || [];
      case TableModeType.RobotAccounts:
        return robotAccounts || [];
      case TableModeType.Invited:
        return invited || [];
      default:
        return allMembers || [];
    }
  }, [tableMode, allMembers, teamMembers, robotAccounts, invited]);

  const {
    paginatedData: paginatedCurrentMembers,
    getSortableSort,
    paginationProps,
  } = usePaginatedSortableTable(currentDataSource, {
    columns: {
      1: (item: ITeamMember) => item.name, // Team member
      2: (item: ITeamMember) => getAccountTypeForMember(item), // Account
    },
    initialPerPage: 20,
    initialSort: {columnIndex: 1, direction: 'asc'}, // Default sort: Team member ascending
    filter: search.query
      ? (item: ITeamMember) => item.name.includes(search.query)
      : undefined,
  });

  const {teams} = useFetchTeams(organizationName);

  // Use the paginated data from our sortable table hook
  const tableMembersList = paginatedCurrentMembers;
  const allMembersList = currentDataSource;
  const [selectedTeamMembers, setSelectedTeamMembers] = useState<ITeamMember[]>(
    [],
  );
  const {addAlert} = useUI();

  const [isEditing, setIsEditing] = useState(false);
  const [teamDescr, setTeamDescr] = useState<string>();
  const [isDeleteModalForRowOpen, setIsDeleteModalForRowOpen] = useState(false);
  const [memberToBeDeleted, setMemberToBeDeleted] = useState<IMemberInfo>();

  // Team Sync states
  const [isDirectoryTeamSyncModalOpen, setIsDirectoryTeamSyncModalOpen] =
    useState(false);
  const [directoryGroupName, setDirectoryGroupName] = useState<string>('');
  const [teamSyncLastUpdated, setTeamSyncLastUpdated] =
    useState<string>('Never');
  const [pageInReadOnlyMode, setPageInReadOnlyMode] = useState<boolean>(false);
  const [isRemoveTeamSyncModalOpen, setRemoveTeamSyncModalOpen] =
    useState<boolean>(false);
  const [teamSyncConfigExpanded, setTeamSyncConfigExpanded] = useState(true);

  // No longer needed - data is managed by usePaginatedSortableTable hook

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
      setIsDirectoryTeamSyncModalOpen(false);
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
      if (teamSyncInfo.service === 'oidc') {
        setDirectoryGroupName(
          (teamSyncInfo.config as {group_name?: string})?.group_name,
        );
      } else if (teamSyncInfo.service === 'ldap') {
        setDirectoryGroupName(
          (teamSyncInfo.config as {group_dn?: string})?.group_dn,
        );
      } else if (teamSyncInfo.service === 'keystone') {
        setDirectoryGroupName(
          (teamSyncInfo.config as {group_id?: string})?.group_id,
        );
      }
      if (teamSyncInfo.last_updated !== null) {
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
    config?.features?.TEAM_SYNCING &&
    teamCanSync !== null &&
    !teamSyncInfo &&
    config?.registry_state !== 'readonly';

  const fetchSyncBtn = () => {
    const result = [];
    if (displaySyncDirectory) {
      result.push(
        <Button
          variant="link"
          onClick={() =>
            setIsDirectoryTeamSyncModalOpen(!isDirectoryTeamSyncModalOpen)
          }
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
      <Conditional if={teamSyncInfo?.config}>
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
                    {directoryGroupName}
                  </TextListItem>
                  {teamSyncInfo?.service !== 'oidc' && (
                    <>
                      <TextListItem component={TextListItemVariants.dt}>
                        Last Updated
                      </TextListItem>
                      <TextListItem component={TextListItemVariants.dd}>
                        {!teamSyncLastUpdated ||
                        teamSyncLastUpdated === 'Never' ? (
                          <Flex spaceItems={{default: 'spaceItemsSm'}}>
                            <FlexItem>
                              <Spinner size="md" />
                            </FlexItem>
                            <FlexItem>Waiting for first sync...</FlexItem>
                          </Flex>
                        ) : (
                          <Tooltip content={formatDate(teamSyncLastUpdated)}>
                            <span>
                              {formatRelativeTime(teamSyncLastUpdated)}
                            </span>
                          </Tooltip>
                        )}
                      </TextListItem>
                    </>
                  )}
                </TextList>
              </TextContent>
            </AccordionContent>
          </AccordionItem>
        </Accordion>
      </Conditional>
    </>
  );

  const serviceDisplayName = getServiceDisplayName(
    (teamCanSync?.service || 'oidc') as SupportedService,
  );
  const groupFieldLabel = getGroupFieldLabel(
    (teamCanSync?.service || 'oidc') as SupportedService,
    teamCanSync?.issuer_domain,
  );

  const directoryTeamSyncModalHolder = (
    <DirectoryTeamSyncModal
      isModalOpen={isDirectoryTeamSyncModalOpen}
      toggleModal={() =>
        setIsDirectoryTeamSyncModalOpen(!isDirectoryTeamSyncModalOpen)
      }
      titleText={`Enable ${serviceDisplayName} Team Sync`}
      primaryText={`Team synchronization allows this team's user membership to be backed by a group in ${serviceDisplayName}.`}
      onConfirmSync={(groupName) =>
        enableTeamSync(
          groupName,
          (teamCanSync?.service || 'oidc') as SupportedService,
        )
      }
      secondaryText={
        teamCanSync?.base_dn ? (
          <>
            Enter the {groupFieldLabel} you&apos;d like to sync membership with,
            relative to the base DN: <strong>{teamCanSync.base_dn}</strong>
          </>
        ) : (
          `Enter the ${groupFieldLabel} you'd like to sync membership with:`
        )
      }
      alertText={`Please note that once team syncing is enabled, the membership of users who are already part of the team will be revoked. ${serviceDisplayName} group will be the single source of truth. This is a non-reversible action. Team's user membership from within ${config?.config.REGISTRY_TITLE_SHORT} will be read-only.`}
    />
  );

  if (allMembers?.length === 0) {
    return (
      <>
        <Conditional if={pageInReadOnlyMode}>{teamSyncedConfig}</Conditional>
        <PageSection variant={PageSectionVariants.light}>
          {teamDescriptionComponent}
        </PageSection>
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
        <Conditional if={isDirectoryTeamSyncModalOpen}>
          {directoryTeamSyncModalHolder}
        </Conditional>
        <Conditional if={isRemoveTeamSyncModalOpen && teamCanSync !== null}>
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
          page={paginationProps.page}
          setPage={paginationProps.setPage}
          perPage={paginationProps.perPage}
          setPerPage={paginationProps.setPerPage}
          search={search}
          setSearch={setSearch}
          searchOptions={[manageMemberColumnNames.teamMember]}
          setDrawerContent={props.setDrawerContent}
          isReadOnly={config?.registry_state === 'readonly'}
          isAdmin={organization.is_admin}
          displaySyncDirectory={displaySyncDirectory}
          isDirectoryTeamSyncModalOpen={isDirectoryTeamSyncModalOpen}
          toggleDirectoryTeamSyncModal={() =>
            setIsDirectoryTeamSyncModalOpen(!isDirectoryTeamSyncModalOpen)
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
          <Conditional if={isDirectoryTeamSyncModalOpen}>
            {directoryTeamSyncModalHolder}
          </Conditional>
          <Conditional if={isRemoveTeamSyncModalOpen && teamCanSync !== null}>
            {removeTeamSyncModalHolder}
          </Conditional>
          <Table aria-label="Selectable table" variant="compact">
            <Thead>
              <Tr>
                <Th />
                <Th sort={getSortableSort(1)}>
                  {manageMemberColumnNames.teamMember}
                </Th>
                <Th sort={getSortableSort(2)}>
                  {manageMemberColumnNames.account}
                </Th>
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
