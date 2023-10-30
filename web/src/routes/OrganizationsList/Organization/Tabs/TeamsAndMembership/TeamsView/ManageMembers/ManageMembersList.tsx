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

  const {
    allMembers,
    teamMembers,
    robotAccounts,
    invited,
    paginatedAllMembers,
    paginatedTeamMembers,
    paginatedRobotAccounts,
    paginatedInvited,
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
            />
            <ToggleGroupItem
              text="Robot accounts"
              buttonId={TableModeType.RobotAccounts}
              data-testid={TableModeType.RobotAccounts}
              isSelected={tableMode == TableModeType.RobotAccounts}
              onChange={onTableModeChange}
            />
            <ToggleGroupItem
              text="Invited"
              buttonId={TableModeType.Invited}
              data-testid={TableModeType.Invited}
              isSelected={tableMode == TableModeType.Invited}
              onChange={onTableModeChange}
            />
          </ToggleGroup>
        </ToolbarItem>
      </ToolbarContent>
    </Toolbar>
  );

  const {updateTeamDetails, errorUpdateTeamDetails, successUpdateTeamDetails} =
    useUpdateTeamDetails(organizationName);

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

  const teamDescriptionComponent = (
    <ToolbarContent className="team-description-padding">
      <Flex>
        <FlexItem spacer={{default: 'spacerNone'}}>
          <Title data-testid="teamname-title" headingLevel="h3">
            {teamName}
          </Title>
        </FlexItem>
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

  if (allMembers?.length === 0) {
    return (
      <Empty
        title="There are no viewable members for this team"
        icon={CubesIcon}
        body="Either no team members exist yet or you may not have permission to view any."
        button={
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
        }
      />
    );
  }

  return (
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
      >
        {viewToggle}
        {teamDescriptionComponent}
        <Conditional if={isDeleteModalForRowOpen}>{deleteRowModal}</Conditional>
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
            {tableMembersList.map((teamMember, rowIndex) => (
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
              </Tr>
            ))}
          </Tbody>
        </Table>
      </ManageMembersToolbar>
    </PageSection>
  );
}
interface ManageMembersListProps {
  setDrawerContent?: (contentType: OrganizationDrawerContentType) => void;
}
