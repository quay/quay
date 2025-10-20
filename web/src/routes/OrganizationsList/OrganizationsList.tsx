import {
  Button,
  DropdownItem,
  Modal,
  ModalVariant,
  PageSection,
  PageSectionVariants,
  PanelFooter,
  Title,
} from '@patternfly/react-core';
import PropTypes from 'prop-types';
import {CubesIcon} from '@patternfly/react-icons';
import {Table, Tbody, Td, Th, Thead, Tr} from '@patternfly/react-table';
import {usePaginatedSortableTable} from '../../hooks/usePaginatedSortableTable';
import {useEffect, useState} from 'react';
import {useRecoilState, useRecoilValue} from 'recoil';
import {
  searchOrgsFilterState,
  selectedOrgsState,
} from 'src/atoms/OrganizationListState';
import {LoadingPage} from 'src/components/LoadingPage';
import RepoCount from 'src/components/Table/RepoCount';
import {QuayBreadcrumb} from 'src/components/breadcrumb/Breadcrumb';
import Empty from 'src/components/empty/Empty';
import ErrorModal from 'src/components/errors/ErrorModal';
import RequestError from 'src/components/errors/RequestError';
import {BulkDeleteModalTemplate} from 'src/components/modals/BulkDeleteModalTemplate';
import {ToolbarButton} from 'src/components/toolbar/ToolbarButton';
import {ToolbarPagination} from 'src/components/toolbar/ToolbarPagination';
import {useOrganizations} from 'src/hooks/UseOrganizations';
import {useCurrentUser} from 'src/hooks/UseCurrentUser';
import {useQuayConfig} from 'src/hooks/UseQuayConfig';
import {
  useRegistrySize,
  useQueueRegistrySizeCalculation,
} from 'src/hooks/UseRegistrySize';
import {BulkOperationError, addDisplayError} from 'src/resources/ErrorHandling';
import {formatSize} from 'src/libs/utils';
import {IOrganization} from 'src/resources/OrganizationResource';
import ColumnNames from './ColumnNames';
import {CreateOrganizationModal} from './CreateOrganizationModal';
import {OrganizationToolBar} from './OrganizationToolBar';
import OrgTableData from './OrganizationsListTableData';
import './css/Organizations.scss';

export interface OrganizationsTableItem {
  name: string;
  isUser: boolean;
}

function OrgListHeader({
  registrySize,
  formatLastRan,
  getRegistrySizeStatus,
  handleCalculateClick,
  isQueuing,
  showRegistrySize,
}) {
  return (
    <>
      <QuayBreadcrumb />
      <PageSection variant={PageSectionVariants.light} hasShadowBottom>
        <div className="co-m-nav-title--row pf-v5-u-display-flex pf-v5-u-justify-content-space-between pf-v5-u-align-items-flex-end">
          <Title headingLevel="h1">Organizations!!!</Title>

          {/* Registry Size Display - Inline with header for superusers */}
          {showRegistrySize && (
            <div className="pf-v5-u-font-size-sm pf-v5-u-mb-xs">
              <span>
                Total Registry Size:{' '}
                {registrySize
                  ? formatSize(registrySize.size_bytes)
                  : '0.00 KiB'}
                , Updated: {formatLastRan(registrySize?.last_ran || null)}
                {getRegistrySizeStatus()}
              </span>{' '}
              <Button
                variant="primary"
                size="sm"
                onClick={handleCalculateClick}
                isDisabled={isQueuing}
                className="pf-v5-u-ml-md"
              >
                {isQueuing ? 'Calculating...' : 'Calculate'}
              </Button>
            </div>
          )}
        </div>
      </PageSection>
    </>
  );
}

OrgListHeader.propTypes = {
  registrySize: PropTypes.object,
  formatLastRan: PropTypes.func.isRequired,
  getRegistrySizeStatus: PropTypes.func.isRequired,
  handleCalculateClick: PropTypes.func.isRequired,
  isQueuing: PropTypes.bool.isRequired,
  showRegistrySize: PropTypes.bool.isRequired,
};

export default function OrganizationsList() {
  const [isOrganizationModalOpen, setOrganizationModalOpen] = useState(false);
  const [selectedOrganization, setSelectedOrganization] =
    useRecoilState(selectedOrgsState);
  const [err, setErr] = useState<string[]>();
  const [deleteModalIsOpen, setDeleteModalIsOpen] = useState(false);
  const [isKebabOpen, setKebabOpen] = useState(false);
  const [isCalculateModalOpen, setCalculateModalOpen] = useState(false);

  // Get current user for superuser check
  const {user} = useCurrentUser();
  const quayConfig = useQuayConfig();

  // Registry size data (only fetch if superuser)
  const {registrySize, refetch: refetchRegistrySize} = useRegistrySize();

  // Registry size calculation mutation
  const {queueCalculation, isQueuing} = useQueueRegistrySizeCalculation({
    onSuccess: () => {
      setCalculateModalOpen(false);
      // Refetch after a short delay to allow backend processing
      setTimeout(() => refetchRegistrySize(), 1000);
    },
    onError: (errorMsg) => {
      setErr([errorMsg]);
      setCalculateModalOpen(false);
    },
  });
  const {
    organizationsTableDetails,
    loading,
    error,
    totalResults,
    search,
    setSearch,
    deleteOrganizations,
  } = useOrganizations();

  const searchFilter = useRecoilValue(searchOrgsFilterState);

  // Helper function to format the last updated time
  const formatLastRan = (lastRan: number | null): string => {
    if (!lastRan) return 'Never';
    const date = new Date(lastRan);
    return `${date.toLocaleDateString('en-US')} ${date.toLocaleTimeString(
      'en-US',
    )}`;
  };

  // Helper function to get registry size status text
  const getRegistrySizeStatus = () => {
    if (!registrySize) return '';

    if (registrySize.running) return ', Calculating...';
    if (registrySize.queued) return ', Calculation queued';
    if (
      !registrySize.last_ran &&
      !registrySize.queued &&
      !registrySize.running
    ) {
      return ', Calculation required';
    }
    return '';
  };

  // Handle calculate button click
  const handleCalculateClick = () => {
    setCalculateModalOpen(true);
  };

  // Confirm registry size calculation
  const confirmCalculation = () => {
    queueCalculation();
  };

  // Use unified table hook for sorting and pagination (Name column only)
  const {
    paginatedData: paginatedOrganizationsList,
    sortedData: sortedOrgs,
    getSortableSort,
    paginationProps,
  } = usePaginatedSortableTable(organizationsTableDetails || [], {
    columns: {
      1: (org) => org.name, // Name column only
    },
    filter: searchFilter,
    initialPerPage: 20,
  });

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

  const handleOrgDeletion = async () => {
    const orgs = selectedOrganization.map((org) => org.name);
    try {
      await deleteOrganizations(orgs);
      setDeleteModalIsOpen(!deleteModalIsOpen);
      setSelectedOrganization([]);
    } catch (err) {
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
    }
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
        <OrgListHeader
          registrySize={null}
          formatLastRan={() => 'Never'}
          getRegistrySizeStatus={() => ''}
          handleCalculateClick={() => undefined}
          isQueuing={false}
          showRegistrySize={false}
        />
        <LoadingPage />
      </>
    );
  }

  // Return component Error state
  if (error) {
    return (
      <>
        <OrgListHeader
          registrySize={null}
          formatLastRan={() => 'Never'}
          getRegistrySizeStatus={() => ''}
          handleCalculateClick={() => undefined}
          isQueuing={false}
          showRegistrySize={false}
        />
        <RequestError message={error as string} />
      </>
    );
  }

  // Return component Empty state
  if (!loading && !organizationsTableDetails?.length) {
    return (
      <>
        <OrgListHeader
          registrySize={null}
          formatLastRan={() => 'Never'}
          getRegistrySizeStatus={() => ''}
          handleCalculateClick={() => undefined}
          isQueuing={false}
          showRegistrySize={false}
        />
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
      <OrgListHeader
        registrySize={registrySize}
        formatLastRan={formatLastRan}
        getRegistrySizeStatus={getRegistrySizeStatus}
        handleCalculateClick={handleCalculateClick}
        isQueuing={isQueuing}
        showRegistrySize={
          user?.super_user &&
          quayConfig?.features?.QUOTA_MANAGEMENT &&
          quayConfig?.features?.EDIT_QUOTA
        }
      />
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
          organizationsList={sortedOrgs}
          perPage={paginationProps.perPage}
          page={paginationProps.page}
          setPage={paginationProps.setPage}
          setPerPage={paginationProps.setPerPage}
          setSelectedOrganization={setSelectedOrganization}
          paginatedOrganizationsList={paginatedOrganizationsList}
          onSelectOrganization={onSelectOrganization}
        />
        <Table aria-label="Selectable table" variant="compact">
          <Thead>
            <Tr>
              <Th />
              <Th sort={getSortableSort(1)} modifier="wrap">
                {ColumnNames.name}
              </Th>
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
                    isDisabled: !isOrgSelectable(org),
                  }}
                />
                <OrgTableData
                  name={org.name}
                  isUser={org.isUser}
                ></OrgTableData>
              </Tr>
            ))}
          </Tbody>
        </Table>
        <PanelFooter>
          <ToolbarPagination
            itemsList={sortedOrgs}
            {...paginationProps}
            bottom={true}
          />
        </PanelFooter>
      </PageSection>

      {/* Calculate Registry Size Confirmation Modal */}
      <Modal
        variant={ModalVariant.small}
        title="Confirm Registry Size Calculation"
        isOpen={isCalculateModalOpen}
        onClose={() => setCalculateModalOpen(false)}
        actions={[
          <Button
            key="confirm"
            variant="primary"
            onClick={confirmCalculation}
            isDisabled={isQueuing}
          >
            {isQueuing ? 'Queuing...' : 'Calculate'}
          </Button>,
          <Button
            key="cancel"
            variant="link"
            onClick={() => setCalculateModalOpen(false)}
          >
            Cancel
          </Button>,
        ]}
      >
        <p>Are you sure you want to queue registry size calculation?</p>
        <p style={{color: 'red', marginTop: '1em'}}>
          This is a database intensive operation. Use with caution.
        </p>
      </Modal>
    </>
  );
}
