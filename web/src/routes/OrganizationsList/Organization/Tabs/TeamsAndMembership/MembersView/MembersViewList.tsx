import {Table, Tbody, Td, Th, Thead, Tr} from '@patternfly/react-table';
import {Link, useSearchParams} from 'react-router-dom';
import {
  Label,
  PageSection,
  PageSectionVariants,
  PanelFooter,
  Popover,
  Spinner,
} from '@patternfly/react-core';
import {useEffect, useState} from 'react';
import MembersViewToolbar from './MembersViewToolbar';
import {useFetchMembers} from 'src/hooks/UseMembers';
import {IMemberTeams, IMembers} from 'src/resources/MembersResource';
import {useAlerts} from 'src/hooks/UseAlerts';
import {AlertVariant} from 'src/atoms/AlertState';
import {getTeamMemberPath} from 'src/routes/NavigationPath';
import {ToolbarPagination} from 'src/components/toolbar/ToolbarPagination';
import Conditional from 'src/components/empty/Conditional';

export const memberViewColumnNames = {
  username: 'User name',
  teams: 'Teams',
  directRepositoryPermissions: 'Direct repository permissions',
};

export default function MembersViewList(props: MembersViewListProps) {
  const {
    filteredMembers,
    paginatedMembers,
    loading,
    error,
    page,
    setPage,
    perPage,
    setPerPage,
    search,
    setSearch,
  } = useFetchMembers(props.organizationName);

  const [selectedMembers, setSelectedMembers] = useState<IMembers[]>([]);
  const [isPopoverOpen, setPopoverOpen] = useState(false);
  const [searchParams] = useSearchParams();
  const {addAlert} = useAlerts();

  useEffect(() => {
    if (error) {
      addAlert({
        variant: AlertVariant.Failure,
        title: `Could not load members`,
      });
    }
  }, [error]);

  const handleClick = () => {
    setPopoverOpen(!isPopoverOpen);
  };

  const onSelectMember = (
    member: IMembers,
    rowIndex: number,
    isSelecting: boolean,
  ) => {
    setSelectedMembers((prevSelected) => {
      const otherSelectedMembers = prevSelected.filter(
        (m) => m.name !== member.name,
      );
      return isSelecting
        ? [...otherSelectedMembers, member]
        : otherSelectedMembers;
    });
  };

  if (loading) {
    return <Spinner />;
  }

  const renderTeamLabels = (teamsArr: IMemberTeams[], rowIndex: number) => {
    const labelsToRender = teamsArr.slice(0, 4);
    const remainingLabels = teamsArr.slice(4);

    const labelsToDisplay = labelsToRender.map((team, idx) => (
      <Link
        to={getTeamMemberPath(
          location.pathname,
          props.organizationName,
          team.name,
          searchParams.get('tab'),
        )}
        key={idx * 4}
      >
        <Label key={team.name} color="blue">
          {team.name}
        </Label>{' '}
      </Link>
    ));

    if (remainingLabels?.length) {
      labelsToDisplay.push(
        <Label
          key={rowIndex}
          color="blue"
          onClick={handleClick}
          id={'team-popover'}
        >
          {remainingLabels.length} more{' '}
          {isPopoverOpen ? (
            <Popover
              key={rowIndex}
              headerContent={''}
              bodyContent={remainingLabels.map((team, i) => (
                <Link
                  key={i}
                  to={getTeamMemberPath(
                    location.pathname,
                    props.organizationName,
                    team.name,
                    searchParams.get('tab'),
                  )}
                >
                  <Label key={team.name} color="blue">
                    {team.name}
                  </Label>{' '}
                </Link>
              ))}
              isVisible={isPopoverOpen}
              shouldClose={handleClick}
              triggerRef={() =>
                document.getElementById('team-popover') as HTMLButtonElement
              }
            />
          ) : null}
        </Label>,
      );
    }
    return labelsToDisplay;
  };

  return (
    <>
      <PageSection variant={PageSectionVariants.light}>
        <MembersViewToolbar
          selectedMembers={selectedMembers}
          deSelectAll={() => setSelectedMembers([])}
          allItems={filteredMembers}
          paginatedItems={paginatedMembers}
          onItemSelect={onSelectMember}
          page={page}
          setPage={setPage}
          perPage={perPage}
          setPerPage={setPerPage}
          search={search}
          setSearch={setSearch}
          searchOptions={[memberViewColumnNames.username]}
          handleModalToggle={props.handleModalToggle}
        />
        {props.children}
        <Table aria-label="Selectable table" variant="compact">
          <Thead>
            <Tr>
              <Th />
              <Th>{memberViewColumnNames.username}</Th>
              <Th>{memberViewColumnNames.teams}</Th>
              <Th>{memberViewColumnNames.directRepositoryPermissions}</Th>
            </Tr>
          </Thead>
          <Tbody>
            {paginatedMembers?.map((member, rowIndex) => (
              <Tr key={rowIndex}>
                <Td
                  select={{
                    rowIndex,
                    onSelect: (_event, isSelecting) =>
                      onSelectMember(member, rowIndex, isSelecting),
                    isSelected: selectedMembers.some(
                      (t) => t.name === member.name,
                    ),
                  }}
                />
                <Td dataLabel={memberViewColumnNames.username}>
                  {member.name}
                </Td>
                <Td dataLabel={memberViewColumnNames.teams}>
                  {renderTeamLabels(member.teams, rowIndex)}
                </Td>
                <Td
                  dataLabel={memberViewColumnNames.directRepositoryPermissions}
                >
                  Direct permissions on {member.repositories?.length}{' '}
                  repositories under this organization
                </Td>
              </Tr>
            ))}
          </Tbody>
        </Table>
        <PanelFooter>
          <ToolbarPagination
            itemsList={filteredMembers}
            perPage={perPage}
            page={page}
            setPage={setPage}
            setPerPage={setPerPage}
            bottom={true}
          />
        </PanelFooter>
      </PageSection>
    </>
  );
}

interface MembersViewListProps {
  organizationName: string;
  children?: React.ReactNode;
  handleModalToggle: () => void;
}
