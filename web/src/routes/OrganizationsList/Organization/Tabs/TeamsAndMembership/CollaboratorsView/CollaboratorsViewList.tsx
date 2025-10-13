import {
  Button,
  PageSection,
  PanelFooter,
  Spinner,
} from '@patternfly/react-core';
import CollaboratorsViewToolbar from './CollaboratorsViewToolbar';
import {Table, Tbody, Td, Th, Thead, Tr} from '@patternfly/react-table';
import {useFetchCollaborators} from 'src/hooks/UseMembers';
import {useEffect, useState} from 'react';
import {IMembers} from 'src/resources/MembersResource';
import {TrashIcon} from '@patternfly/react-icons';
import {useAlerts} from 'src/hooks/UseAlerts';
import {AlertVariant} from 'src/atoms/AlertState';
import {ToolbarPagination} from 'src/components/toolbar/ToolbarPagination';
import CollaboratorsDeleteModal from './CollaboratorsDeleteModal';
import Conditional from 'src/components/empty/Conditional';
import {usePaginatedSortableTable} from '../../../../../../hooks/usePaginatedSortableTable';

export const collaboratorViewColumnNames = {
  username: 'User name',
  directRepositoryPermissions: 'Direct repository permissions',
};

export default function CollaboratorsViewList(
  props: CollaboratorsViewListProps,
) {
  const [isDeleteModalOpen, setIsDeleteModalOpen] = useState(false);

  const {collaborators, loading, error, search, setSearch} =
    useFetchCollaborators(props.organizationName);

  const searchFilter =
    search.query !== ''
      ? (collaborator: IMembers) =>
          collaborator.name.toLowerCase().includes(search.query.toLowerCase())
      : undefined;

  const {
    paginatedData: paginatedCollaborators,
    filteredData: filteredCollaborators,
    getSortableSort,
    paginationProps,
  } = usePaginatedSortableTable(collaborators || [], {
    columns: {
      1: (item: IMembers) => item.name, // User name
      2: (item: IMembers) => item.repositories?.length || 0, // Direct repository permissions count
    },
    filter: searchFilter,
    initialPerPage: 20,
    initialSort: {columnIndex: 1, direction: 'asc'}, // Default sort: User name ascending
  });

  const [selectedCollaborators, setSelectedCollaborators] = useState<
    IMembers[]
  >([]);
  const {addAlert} = useAlerts();
  const [collaboratorToBeDeleted, setCollaboratorToBeDeleted] =
    useState<IMembers>();

  useEffect(() => {
    if (error) {
      addAlert({
        variant: AlertVariant.Failure,
        title: `Could not load collaborators`,
      });
    }
  }, [error]);

  const onSelectCollaborator = (
    collaborator: IMembers,
    rowIndex: number,
    isSelecting: boolean,
  ) => {
    setSelectedCollaborators((prevSelected) => {
      const otherSelectedCollaborators = prevSelected.filter(
        (m) => m.name !== collaborator.name,
      );
      return isSelecting
        ? [...otherSelectedCollaborators, collaborator]
        : otherSelectedCollaborators;
    });
  };

  const deleteCollabModal = (
    <CollaboratorsDeleteModal
      isModalOpen={isDeleteModalOpen}
      toggleModal={() => setIsDeleteModalOpen(!isDeleteModalOpen)}
      collaborator={collaboratorToBeDeleted}
      organizationName={props.organizationName}
    />
  );

  if (loading) {
    return <Spinner />;
  }

  return (
    <>
      <PageSection hasBodyWrapper={false}>
        <CollaboratorsViewToolbar
          selectedMembers={selectedCollaborators}
          deSelectAll={() => setSelectedCollaborators([])}
          allItems={filteredCollaborators}
          paginatedItems={paginatedCollaborators}
          onItemSelect={onSelectCollaborator}
          page={paginationProps.page}
          setPage={paginationProps.setPage}
          perPage={paginationProps.perPage}
          setPerPage={paginationProps.setPerPage}
          search={search}
          setSearch={setSearch}
          searchOptions={[collaboratorViewColumnNames.username]}
          handleModalToggle={props.handleModalToggle}
        />
        {props.children}
        <Conditional if={isDeleteModalOpen}>{deleteCollabModal}</Conditional>
        <Table aria-label="Selectable table" variant="compact">
          <Thead>
            <Tr>
              <Th />
              <Th sort={getSortableSort(1)}>
                {collaboratorViewColumnNames.username}
              </Th>
              <Th sort={getSortableSort(2)}>
                {collaboratorViewColumnNames.directRepositoryPermissions}
              </Th>
              <Th></Th>
            </Tr>
          </Thead>
          <Tbody>
            {paginatedCollaborators?.map((collaborator, rowIndex) => (
              <Tr key={rowIndex}>
                <Td
                  select={{
                    rowIndex,
                    onSelect: (_event, isSelecting) =>
                      onSelectCollaborator(collaborator, rowIndex, isSelecting),
                    isSelected: selectedCollaborators.some(
                      (t) => t.name === collaborator.name,
                    ),
                  }}
                />
                <Td dataLabel={collaboratorViewColumnNames.username}>
                  {collaborator.name}
                </Td>
                <Td
                  dataLabel={
                    collaboratorViewColumnNames.directRepositoryPermissions
                  }
                >
                  Direct permissions on {collaborator.repositories?.length}{' '}
                  repositories under this organization
                </Td>
                <Td>
                  <Button
                    icon={<TrashIcon />}
                    variant="plain"
                    onClick={() => {
                      setCollaboratorToBeDeleted(collaborator);
                      setIsDeleteModalOpen(true);
                    }}
                    data-testid={`${collaborator.name}-del-icon`}
                  />
                </Td>
              </Tr>
            ))}
          </Tbody>
        </Table>
        <PanelFooter>
          <ToolbarPagination
            itemsList={filteredCollaborators}
            perPage={paginationProps.perPage}
            page={paginationProps.page}
            setPage={paginationProps.setPage}
            setPerPage={paginationProps.setPerPage}
            bottom={true}
          />
        </PanelFooter>
      </PageSection>
    </>
  );
}

interface CollaboratorsViewListProps {
  organizationName: string;
  children?: React.ReactNode;
  handleModalToggle: () => void;
}
