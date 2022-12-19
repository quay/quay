import {
  TableComposable,
  Thead,
  Tr,
  Th,
  Tbody,
  Td,
} from '@patternfly/react-table';
import {
  PageSection,
  PageSectionVariants,
  Title,
  DropdownItem,
  PanelFooter,
} from '@patternfly/react-core';
import './css/Organizations.scss';
import {CreateOrganizationModal} from './CreateOrganizationModal';
import {useRecoilState, useRecoilValue} from 'recoil';
import {selectedOrgsState} from 'src/atoms/UserState';
import {useEffect, useState} from 'react';
import {IOrganization} from 'src/resources/OrganizationResource';
import OrgTableData from './OrganizationsListTableData';
import {BulkDeleteModalTemplate} from 'src/components/modals/BulkDeleteModalTemplate';
import RequestError from 'src/components/errors/RequestError';
import {OrganizationToolBar} from './OrganizationToolBar';
import {CubesIcon} from '@patternfly/react-icons';
import {ToolbarButton} from 'src/components/toolbar/ToolbarButton';
import Empty from 'src/components/empty/Empty';
import {QuayBreadcrumb} from 'src/components/breadcrumb/Breadcrumb';
import {LoadingPage} from 'src/components/LoadingPage';
import {addDisplayError, BulkOperationError} from 'src/resources/ErrorHandling';
import ErrorModal from 'src/components/errors/ErrorModal';
import {ToolbarPagination} from 'src/components/toolbar/ToolbarPagination';
import ColumnNames from './ColumnNames';
import RepoCount from 'src/components/Table/RepoCount';
import {useOrganizations} from 'src/hooks/UseOrganizations';
import {useDeleteOrganizations} from 'src/hooks/UseDeleteOrganizations';

export interface OrganizationsTableItem {
  name: string;
  isUser: boolean;
}

function OrgListHeader() {
  return (
    <>
      <QuayBreadcrumb />
      <PageSection variant={PageSectionVariants.light}>
        <div className="co-m-nav-title--row">
          <Title headingLevel="h1">Organizations</Title>
        </div>
      </PageSection>
    </>
  );
}

export default function OrganizationsList() {
  const [isOrganizationModalOpen, setOrganizationModalOpen] = useState(false);
  const [selectedOrganization, setSelectedOrganization] =
    useRecoilState(selectedOrgsState);
  const [err, setErr] = useState<string[]>();
  const [deleteModalIsOpen, setDeleteModalIsOpen] = useState(false);
  const [isKebabOpen, setKebabOpen] = useState(false);
  const [perPage, setPerPage] = useState<number>(10);
  const [page, setPage] = useState<number>(1);

  const {
    organizationsTableDetails,
    loading,
    error,
    totalResults,
    search,
    setSearch,
  } = useOrganizations();

  const filteredOrgs =
    search.query !== ''
      ? organizationsTableDetails?.filter((repo) =>
          repo.name.includes(search.query),
        )
      : organizationsTableDetails;

  const paginatedOrganizationsList = filteredOrgs?.slice(
    page * perPage - perPage,
    page * perPage - perPage + perPage,
  );

  const isOrgSelectable = (org) => org.name !== ''; // Arbitrary logic for this example

  // Logic for handling row-wise checkbox selection in <Td>
  const isOrganizationSelected = (ns: OrganizationsTableItem) =>
    selectedOrganization.some((org) => org.name === ns.name);

  const setOrganizationChecked = (
    ns: OrganizationsTableItem,
    isSelecting = true,
  ) =>
    setSelectedOrganization((prevSelected) => {
      const otherSelectedOrganizationNames = prevSelected.filter(
        (r) => r.name !== ns.name,
      );
      return isSelecting && isOrgSelectable(ns)
        ? [...otherSelectedOrganizationNames, ns]
        : otherSelectedOrganizationNames;
    });

  // To allow shift+click to select/deselect multiple rows
  const [recentSelectedRowIndex, setRecentSelectedRowIndex] = useState<
    number | null
  >(null);
  const [shifting, setShifting] = useState(false);

  const onSelectOrganization = (
    currentOrganization: OrganizationsTableItem,
    rowIndex: number,
    isSelecting: boolean,
  ) => {
    // If the user is shift + selecting the checkboxes, then all intermediate checkboxes should be selected
    if (shifting && recentSelectedRowIndex !== null) {
      const numberSelected = rowIndex - recentSelectedRowIndex;
      const intermediateIndexes =
        numberSelected > 0
          ? Array.from(
              new Array(numberSelected + 1),
              (_x, i) => i + recentSelectedRowIndex,
            )
          : Array.from(
              new Array(Math.abs(numberSelected) + 1),
              (_x, i) => i + rowIndex,
            );
      intermediateIndexes.forEach((index) =>
        setOrganizationChecked(organizationsTableDetails[index], isSelecting),
      );
    } else {
      setOrganizationChecked(currentOrganization, isSelecting);
    }
    setRecentSelectedRowIndex(rowIndex);
  };

  const {deleteOrganizations} = useDeleteOrganizations({
    onSuccess: () => {
      setDeleteModalIsOpen(!deleteModalIsOpen);
      setSelectedOrganization([]);
    },
    onError: (err) => {
      console.error(err);
      if (err instanceof BulkOperationError) {
        const errMessages = [];
        // TODO: Would like to use for .. of instead of foreach
        // typescript complains saying we're using version prior to es6?
        err.getErrors().forEach((error, org) => {
          errMessages.push(
            addDisplayError(`Failed to delete org ${org}`, error.error),
          );
        });
        setErr(errMessages);
      } else {
        setErr([addDisplayError('Failed to delete orgs', err)]);
      }
      setDeleteModalIsOpen(!deleteModalIsOpen);
      setSelectedOrganization([]);
    },
  });

  const handleOrgDeletion = async () => {
    const orgs = selectedOrganization.map((org) => org.name);
    await deleteOrganizations(orgs);
  };

  const handleDeleteModalToggle = () => {
    setKebabOpen(!isKebabOpen);
    setDeleteModalIsOpen(!deleteModalIsOpen);
  };

  const kebabItems = [
    <DropdownItem key="delete" onClick={handleDeleteModalToggle}>
      Delete
    </DropdownItem>,
  ];

  /* Mapper object used to render bulk delete table
    - keys are actual column names of the table
    - value is an object type with a "label" which maps to the attributes of <T>
      and an optional "transformFunc" which can be used to modify the value being displayed */
  const mapOfColNamesToTableData = {
    Organization: {label: 'name'},
    'Repo Count': {
      transformFunc: (org: IOrganization) => <RepoCount name={org.name} />,
    },
  };

  const createOrgModal = (
    <CreateOrganizationModal
      isModalOpen={isOrganizationModalOpen}
      handleModalToggle={() =>
        setOrganizationModalOpen(!isOrganizationModalOpen)
      }
    />
  );

  const deleteModal = (
    <BulkDeleteModalTemplate
      mapOfColNamesToTableData={mapOfColNamesToTableData}
      handleModalToggle={() => setDeleteModalIsOpen(!deleteModalIsOpen)}
      handleBulkDeletion={handleOrgDeletion}
      isModalOpen={deleteModalIsOpen}
      selectedItems={organizationsTableDetails?.filter((org) =>
        selectedOrganization.some(
          (selectedOrg) => org.name === selectedOrg.name,
        ),
      )}
      resourceName={'organizations'}
    />
  );
  useEffect(() => {
    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Shift') {
        setShifting(true);
      }
    };
    const onKeyUp = (e: KeyboardEvent) => {
      if (e.key === 'Shift') {
        setShifting(false);
      }
    };

    document.addEventListener('keydown', onKeyDown);
    document.addEventListener('keyup', onKeyUp);

    return () => {
      document.removeEventListener('keydown', onKeyDown);
      document.removeEventListener('keyup', onKeyUp);
    };
  }, []);

  // Return component Loading state
  if (loading) {
    return (
      <>
        <OrgListHeader />
        <LoadingPage />
      </>
    );
  }

  // Return component Error state
  if (error) {
    return (
      <>
        <OrgListHeader />
        <RequestError message={error as string} />
      </>
    );
  }

  // Return component Empty state
  if (!loading && !organizationsTableDetails?.length) {
    return (
      <>
        <OrgListHeader />
        <Empty
          icon={CubesIcon}
          title="Collaborate and share projects across teams"
          body="Create a shared space of public and private repositories for your developers to collaborate in. Organizations make it easy to add and manage people and permissions"
          button={
            <ToolbarButton
              id="create-organization-button"
              buttonValue="Create Organization"
              Modal={createOrgModal}
              isModalOpen={isOrganizationModalOpen}
              setModalOpen={setOrganizationModalOpen}
            />
          }
        />
      </>
    );
  }

  return (
    <>
      <OrgListHeader />
      <ErrorModal title="Org deletion failed" error={err} setError={setErr} />
      <PageSection variant={PageSectionVariants.light}>
        <OrganizationToolBar
          search={search}
          setSearch={setSearch}
          total={totalResults}
          createOrgModal={createOrgModal}
          isOrganizationModalOpen={isOrganizationModalOpen}
          setOrganizationModalOpen={setOrganizationModalOpen}
          isKebabOpen={isKebabOpen}
          setKebabOpen={setKebabOpen}
          kebabItems={kebabItems}
          selectedOrganization={selectedOrganization}
          deleteKebabIsOpen={deleteModalIsOpen}
          deleteModal={deleteModal}
          organizationsList={filteredOrgs}
          perPage={perPage}
          page={page}
          setPage={setPage}
          setPerPage={setPerPage}
          setSelectedOrganization={setSelectedOrganization}
          paginatedOrganizationsList={paginatedOrganizationsList}
          onSelectOrganization={onSelectOrganization}
        />
        <TableComposable aria-label="Selectable table">
          <Thead>
            <Tr>
              <Th />
              <Th>{ColumnNames.name}</Th>
              <Th>{ColumnNames.repoCount}</Th>
              <Th>{ColumnNames.teamsCount}</Th>
              <Th>{ColumnNames.membersCount}</Th>
              <Th>{ColumnNames.robotsCount}</Th>
              <Th>{ColumnNames.lastModified}</Th>
            </Tr>
          </Thead>
          <Tbody>
            {paginatedOrganizationsList?.map((org, rowIndex) => (
              <Tr key={org.name}>
                <Td
                  select={{
                    rowIndex,
                    onSelect: (_event, isSelecting) =>
                      onSelectOrganization(org, rowIndex, isSelecting),
                    isSelected: isOrganizationSelected(org),
                    disable: !isOrgSelectable(org),
                  }}
                />
                <OrgTableData
                  name={org.name}
                  isUser={org.isUser}
                ></OrgTableData>
              </Tr>
            ))}
          </Tbody>
        </TableComposable>
        <PanelFooter>
          <ToolbarPagination
            itemsList={filteredOrgs}
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
