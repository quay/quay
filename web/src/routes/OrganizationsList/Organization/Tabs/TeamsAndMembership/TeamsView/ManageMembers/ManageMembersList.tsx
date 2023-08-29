import {
  Button,
  PageSection,
  PageSectionVariants,
  Spinner,
  ToggleGroup,
  ToggleGroupItem,
  ToggleGroupItemProps,
  Toolbar,
  ToolbarContent,
  ToolbarItem,
} from '@patternfly/react-core';
import {useEffect, useState} from 'react';
import ManageMembersToolbar from './ManageMembersToolbar';
import {
  TableComposable,
  Tbody,
  Td,
  Th,
  Thead,
  Tr,
} from '@patternfly/react-table';
import {
  ITeamMember,
  useDeleteTeamMember,
  useFetchTeamMembersForOrg,
} from 'src/hooks/UseMembers';
import {CubesIcon, TrashIcon} from '@patternfly/react-icons';
import {useParams} from 'react-router-dom';
import Empty from 'src/components/empty/Empty';
import {useAlerts} from 'src/hooks/UseAlerts';
import {AlertVariant} from 'src/atoms/AlertState';

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

export default function ManageMembersList() {
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

  const [tableMembersList, setTableMembersList] = useState<ITeamMember[]>([]);
  const [allMembersList, setAllMembersList] = useState<ITeamMember[]>([]);
  const [selectedTeamMembers, setSelectedTeamMembers] = useState<ITeamMember[]>(
    [],
  );
  const [tableMode, setTableMode] = useState<TableModeType>(
    TableModeType.AllMembers,
  );
  const {addAlert} = useAlerts();

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
  }, [tableMode, allMembers]);

  const onTableModeChange: ToggleGroupItemProps['onChange'] = (
    _isSelected,
    event,
  ) => {
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
      addAlert({
        variant: AlertVariant.Success,
        title: `Successfully deleted team member`,
      });
    }
  }, [successDeleteTeamMember]);

  useEffect(() => {
    if (errorDeleteTeamMember) {
      addAlert({
        variant: AlertVariant.Failure,
        title: `Error deleting team member`,
      });
    }
  }, [errorDeleteTeamMember]);

  const viewToggle = (
    <Toolbar>
      <ToolbarContent>
        <ToolbarItem spacer={{default: 'spacerMd'}}>
          <ToggleGroup aria-label="Manage members toggle view">
            <ToggleGroupItem
              text="All members"
              buttonId={TableModeType.AllMembers}
              isSelected={tableMode == TableModeType.AllMembers}
              onChange={onTableModeChange}
            />
            <ToggleGroupItem
              text="Team member"
              buttonId={TableModeType.TeamMember}
              isSelected={tableMode == TableModeType.TeamMember}
              onChange={onTableModeChange}
            />
            <ToggleGroupItem
              text="Robot accounts"
              buttonId={TableModeType.RobotAccounts}
              isSelected={tableMode == TableModeType.RobotAccounts}
              onChange={onTableModeChange}
            />
            <ToggleGroupItem
              text="Invited"
              buttonId={TableModeType.Invited}
              isSelected={tableMode == TableModeType.Invited}
              onChange={onTableModeChange}
            />
          </ToggleGroup>
        </ToolbarItem>
      </ToolbarContent>
    </Toolbar>
  );

  const getAccountTypeForMember = (member: ITeamMember): string => {
    if (member.is_robot) {
      return 'Robot account';
    } else if (!member.is_robot && !member.invited) {
      return 'Team member';
    } else if (member.invited) {
      return '(Invited)';
    }
  };

  if (loading) {
    return <Spinner />;
  }

  if (allMembers?.length === 0) {
    return (
      <Empty
        title="There are no viewable members for this team"
        icon={CubesIcon}
        body="Either no team members exist yet or you may not have permission to view any."
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
      >
        {viewToggle}
        <TableComposable aria-label="Selectable table">
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
                <Td dataLabel={manageMemberColumnNames.teamMember}>
                  {teamMember.name}
                </Td>
                <Td dataLabel={manageMemberColumnNames.account}>
                  {getAccountTypeForMember(teamMember)}
                </Td>
                <Td>
                  <Button
                    icon={<TrashIcon />}
                    variant="plain"
                    onClick={() =>
                      removeTeamMember({
                        teamName,
                        memberName: teamMember.name,
                      })
                    }
                    data-testid={`${teamMember.name}-delete-icon`}
                  />
                </Td>
              </Tr>
            ))}
          </Tbody>
        </TableComposable>
      </ManageMembersToolbar>
    </PageSection>
  );
}
