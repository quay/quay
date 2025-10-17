import {ReactElement, useEffect, useState} from 'react';
import {
  PageSection,
  PageSectionVariants,
  Spinner,
  Title,
  PanelFooter,
  DropdownItem,
  Flex,
  FlexItem,
} from '@patternfly/react-core';
import {Table, Tbody, Td, Th, Thead, Tr} from '@patternfly/react-table';
import {useRecoilState} from 'recoil';
import {IRepository} from 'src/resources/RepositoryResource';
import {Link, useLocation} from 'react-router-dom';
import CreateRepositoryModalTemplate from 'src/components/modals/CreateRepoModalTemplate';
import {getRepoDetailPath} from 'src/routes/NavigationPath';
import {selectedReposState} from 'src/atoms/RepositoryState';
import {formatDate, formatSize} from 'src/libs/utils';
import {BulkDeleteModalTemplate} from 'src/components/modals/BulkDeleteModalTemplate';
import {RepositoryToolBar} from 'src/routes/RepositoriesList/RepositoryToolBar';
import {addDisplayError, BulkOperationError} from 'src/resources/ErrorHandling';
import RequestError from 'src/components/errors/RequestError';
import Empty from 'src/components/empty/Empty';
import {CubesIcon} from '@patternfly/react-icons';
import {ToolbarButton} from 'src/components/toolbar/ToolbarButton';
import {QuayBreadcrumb} from 'src/components/breadcrumb/Breadcrumb';
import ErrorModal from 'src/components/errors/ErrorModal';
import {useQuayConfig} from 'src/hooks/UseQuayConfig';
import {ToolbarPagination} from 'src/components/toolbar/ToolbarPagination';
import {RepositoryListColumnNames} from './ColumnNames';
import {useCurrentUser} from 'src/hooks/UseCurrentUser';
import {useRepositories} from 'src/hooks/UseRepositories';
import {useDeleteRepositories} from 'src/hooks/UseDeleteRepositories';
import {usePaginatedSortableTable} from '../../hooks/usePaginatedSortableTable';
import {useFetchOrganizationQuota} from 'src/hooks/UseQuotaManagement';
import {bytesToHumanReadable} from 'src/resources/QuotaResource';
import Avatar from 'src/components/Avatar';
import {generateAvatarFromName} from 'src/libs/avatarUtils';

interface RepoListHeaderProps {
  shouldRender: boolean;
}
function RepoListHeader(props: RepoListHeaderProps) {
  if (!props.shouldRender) {
    return null;
  }
  return (
    <>
      <QuayBreadcrumb />
      <PageSection variant={PageSectionVariants.light} hasShadowBottom>
        <div className="co-m-nav-title--row">
          <Title headingLevel="h1">Repositories</Title>
        </div>
      </PageSection>
    </>
  );
}

export default function RepositoriesList(props: RepositoriesListProps) {
  const currentOrg = props.organizationName;
  const [isCreateRepoModalOpen, setCreateRepoModalOpen] = useState(false);
  const [isKebabOpen, setKebabOpen] = useState(false);
  const [makePublicModalOpen, setmakePublicModal] = useState(false);
  const [makePrivateModalOpen, setmakePrivateModal] = useState(false);
  const [err, setErr] = useState<string[]>();
  const location = useLocation();

  const quayConfig = useQuayConfig();
  const {user} = useCurrentUser();

  // Fetch quota information for the organization
  const {organizationQuota} = useFetchOrganizationQuota(currentOrg);
  const {repos, loading, error, search, setSearch, searchFilter} =
    useRepositories(currentOrg);

  repos?.sort((r1, r2) => {
    return r1.last_modified > r2.last_modified ? -1 : 1;
  });

  const repositoryList: RepoListTableItem[] = repos?.map((repo) => {
    return {
      namespace: repo.namespace,
      name: repo.name,
      is_public: repo.is_public,
      last_modified: repo.last_modified,
      size: repo.quota_report?.quota_bytes,
      configured_quota: repo.quota_report?.configured_quota,
    } as RepoListTableItem;
  });

  // Calculate total quota consumed from all repositories
  const calculateTotalQuotaConsumed = (): number => {
    if (!repos || !Array.isArray(repos)) return 0;
    return repos.reduce((total, repo) => {
      return total + (repo.quota_report?.quota_bytes || 0);
    }, 0);
  };

  const totalQuotaConsumed = calculateTotalQuotaConsumed();

  const formatQuotaDisplay = () => {
    const consumedHuman = bytesToHumanReadable(totalQuotaConsumed);
    const consumedDisplay =
      totalQuotaConsumed > 0
        ? `${consumedHuman.value} ${consumedHuman.unit}`
        : '0.00 KiB';

    if (organizationQuota?.limit_bytes) {
      const totalHuman = bytesToHumanReadable(organizationQuota.limit_bytes);
      const totalDisplay = `${totalHuman.value} ${totalHuman.unit}`;
      const percentage = Math.round(
        (totalQuotaConsumed / organizationQuota.limit_bytes) * 100,
      );
      return `${consumedDisplay} (${percentage}%) of ${totalDisplay}`;
    }

    return consumedDisplay;
  };

  // Use unified table hook for sorting, filtering, and pagination
  const {
    paginatedData: paginatedRepositoryList,
    filteredData: filteredRepos,
    getSortableSort,
    paginationProps,
  } = usePaginatedSortableTable(repositoryList || [], {
    columns: {
      0: (item: RepoListTableItem) =>
        currentOrg == null ? `${item.namespace}/${item.name}` : item.name, // Name
      1: (item: RepoListTableItem) => (item.is_public ? 'public' : 'private'), // Visibility
      2: (item: RepoListTableItem) => item.size || 0, // Size
      3: (item: RepoListTableItem) => item.last_modified || 0, // Last Modified
    },
    initialSort: {columnIndex: 3, direction: 'desc'}, // Default sort: Last Modified descending
    filter: searchFilter,
    initialPerPage: 20,
  });

  useEffect(() => {
    if (search.currentOrganization !== currentOrg) {
      setSearch({...search, query: '', currentOrganization: currentOrg});
    }
  }, [currentOrg]);

  // Select related states
  const [selectedRepoNames, setSelectedRepoNames] =
    useRecoilState(selectedReposState);
  const isRepoSelectable = (repo: IRepository) => repo.name !== ''; // Arbitrary logic for this example
  const selectAllRepos = (isSelecting = true) =>
    setSelectedRepoNames(
      isSelecting ? filteredRepos.map((r) => r.namespace + '/' + r.name) : [],
    );

  const setRepoSelected = (repo: IRepository, isSelecting = true) =>
    setSelectedRepoNames((prevSelected) => {
      const otherSelectedRepoNames = prevSelected.filter(
        (r) => r !== repo.namespace + '/' + repo.name,
      );
      return isSelecting && isRepoSelectable(repo)
        ? [...otherSelectedRepoNames, repo.namespace + '/' + repo.name]
        : otherSelectedRepoNames;
    });

  const isRepoSelected = (repo: IRepository) =>
    selectedRepoNames.includes(repo.namespace + '/' + repo.name);

  const onSelectRepo = (
    repo: IRepository,
    rowIndex: number,
    isSelecting: boolean,
  ) => {
    setRepoSelected(repo, isSelecting);
  };

  const toggleMakePublicClick = () => {
    setmakePublicModal(!makePublicModalOpen);
  };

  const toggleMakePrivateClick = () => {
    setmakePrivateModal(!makePrivateModalOpen);
  };

  const [isDeleteModalOpen, setDeleteModalOpen] = useState(false);

  const handleDeleteModalToggle = () => {
    setKebabOpen(!isKebabOpen);
    setDeleteModalOpen(!isDeleteModalOpen);
  };

  const {deleteRepositories} = useDeleteRepositories({
    onSuccess: () => {
      setSelectedRepoNames([]);
      setDeleteModalOpen(!isDeleteModalOpen);
    },
    onError: (err) => {
      if (err instanceof BulkOperationError) {
        const errMessages = [];
        // TODO: Would like to use for .. of instead of foreach
        // typescript complains saying we're using version prior to es6?
        err.getErrors().forEach((error, repo) => {
          errMessages.push(
            addDisplayError(`Failed to delete repository ${repo}`, error.error),
          );
        });
        setErr(errMessages);
      } else {
        setErr([addDisplayError('Failed to delete repository', err)]);
      }
      setSelectedRepoNames([]);
      setDeleteModalOpen(!isDeleteModalOpen);
    },
  });

  const kebabItems: ReactElement[] = [
    <DropdownItem key="delete" onClick={handleDeleteModalToggle}>
      Delete
    </DropdownItem>,

    <DropdownItem
      key="make public"
      component="button"
      onClick={toggleMakePublicClick}
    >
      Make public
    </DropdownItem>,
    <DropdownItem
      key="make private"
      component="button"
      onClick={toggleMakePrivateClick}
    >
      Make private
    </DropdownItem>,
  ];

  /* Mapper object used to render bulk delete table
    - keys are actual column names of the table
    - value is an object type with a "label" which maps to the attributes of <T>
      and an optional "transformFunc" which can be used to modify the value being displayed */
  const mapOfColNamesToTableData = {
    Repository: {
      label: 'name',
      transformFunc: (item: IRepository) => {
        return `${item.namespace}/${item.name}`;
      },
    },
    Visibility: {
      label: 'is_public',
      transformFunc: (item: IRepository) =>
        item.is_public ? 'public' : 'private',
    },
    Size: {
      label: 'size',
      transformFunc: (item: IRepository) => formatSize(item.size),
    },
  };

  const createRepoModal = (
    <CreateRepositoryModalTemplate
      isModalOpen={isCreateRepoModalOpen}
      handleModalToggle={() => setCreateRepoModalOpen(!isCreateRepoModalOpen)}
      orgName={currentOrg}
      updateListHandler={() => null}
      username={user.username}
      organizations={user.organizations}
    />
  );

  const deleteRepositoryModal = (
    <BulkDeleteModalTemplate
      mapOfColNamesToTableData={mapOfColNamesToTableData}
      handleModalToggle={handleDeleteModalToggle}
      handleBulkDeletion={deleteRepositories}
      isModalOpen={isDeleteModalOpen}
      selectedItems={filteredRepos.filter((repo) =>
        selectedRepoNames.some(
          (selected) => repo.namespace + '/' + repo.name === selected,
        ),
      )}
      resourceName={'repositories'}
    />
  );

  // Return component Error state
  if (error) {
    const errorMessage = error instanceof Error ? error.message : String(error);
    return (
      <>
        <RepoListHeader shouldRender={currentOrg === null} />
        <RequestError message={errorMessage} />
      </>
    );
  }

  // Return component Empty state - only if there are truly no repositories
  // If filtered results are empty but repos exist, show the table with toolbar
  if (!loading && !repos?.length) {
    return (
      <Empty
        icon={CubesIcon}
        title="There are no viewable repositories"
        body="Either no repositories exist yet or you may not have permission to view any. If you have permission, try creating a new repository."
        button={
          <ToolbarButton
            id=""
            buttonValue="Create Repository"
            Modal={createRepoModal}
            isModalOpen={isCreateRepoModalOpen}
            setModalOpen={setCreateRepoModalOpen}
          />
        }
      />
    );
  }

  return (
    <>
      <RepoListHeader shouldRender={currentOrg === null} />
      <PageSection variant={PageSectionVariants.light}>
        <ErrorModal title="Org deletion failed" error={err} setError={setErr} />
        {quayConfig?.features?.QUOTA_MANAGEMENT &&
          quayConfig?.features?.EDIT_QUOTA &&
          currentOrg && (
            <div style={{marginBottom: '1em'}}>
              <Title headingLevel="h4" size="md">
                Total Quota Consumed: <span>{formatQuotaDisplay()}</span>
              </Title>
            </div>
          )}
        <RepositoryToolBar
          search={search}
          setSearch={setSearch}
          total={paginationProps.total}
          currentOrg={currentOrg}
          pageModal={createRepoModal}
          showPageButton={true}
          buttonText="Create Repository"
          isModalOpen={isCreateRepoModalOpen}
          setModalOpen={setCreateRepoModalOpen}
          isKebabOpen={isKebabOpen}
          setKebabOpen={setKebabOpen}
          kebabItems={kebabItems}
          selectedRepoNames={selectedRepoNames}
          deleteModal={deleteRepositoryModal}
          deleteKebabIsOpen={isDeleteModalOpen}
          makePublicModalOpen={makePublicModalOpen}
          toggleMakePublicClick={toggleMakePublicClick}
          makePrivateModalOpen={makePrivateModalOpen}
          toggleMakePrivateClick={toggleMakePrivateClick}
          selectAllRepos={selectAllRepos}
          repositoryList={filteredRepos}
          perPage={paginationProps.perPage}
          page={paginationProps.page}
          setPage={paginationProps.setPage}
          setPerPage={paginationProps.setPerPage}
          setSelectedRepoNames={setSelectedRepoNames}
          paginatedRepositoryList={paginatedRepositoryList}
          onSelectRepo={onSelectRepo}
        />
        <Table aria-label="Selectable table" variant="compact">
          <Thead>
            <Tr>
              <Th />
              <Th modifier="wrap" sort={getSortableSort(0)}>
                {RepositoryListColumnNames.name}
              </Th>
              <Th modifier="wrap" sort={getSortableSort(1)}>
                {RepositoryListColumnNames.visibility}
              </Th>
              {quayConfig?.features.QUOTA_MANAGEMENT &&
              quayConfig?.features.EDIT_QUOTA ? (
                <Th modifier="wrap" sort={getSortableSort(2)}>
                  {RepositoryListColumnNames.size}
                </Th>
              ) : (
                <></>
              )}
              <Th modifier="wrap" sort={getSortableSort(3)}>
                {RepositoryListColumnNames.lastModified}
              </Th>
            </Tr>
          </Thead>
          <Tbody data-testid="repository-list-table">
            {filteredRepos.length === 0 ? (
              // Repo table loading icon
              <Tr>
                <Td>
                  <Spinner size="lg" />
                </Td>
              </Tr>
            ) : (
              paginatedRepositoryList.map((repo, rowIndex) => (
                <Tr key={rowIndex}>
                  <Td
                    select={{
                      rowIndex,
                      onSelect: (_event, isSelecting) =>
                        onSelectRepo(repo, rowIndex, isSelecting),
                      isSelected: isRepoSelected(repo),
                      isDisabled: !isRepoSelectable(repo),
                    }}
                  />
                  <Td dataLabel={RepositoryListColumnNames.name}>
                    <Flex alignItems={{default: 'alignItemsCenter'}}>
                      <FlexItem spacer={{default: 'spacerSm'}}>
                        <Avatar
                          avatar={generateAvatarFromName(
                            currentOrg == null ? repo.namespace : currentOrg,
                          )}
                          size="sm"
                        />
                      </FlexItem>
                      <FlexItem>
                        {currentOrg == null ? (
                          <Link
                            to={getRepoDetailPath(
                              location.pathname,
                              repo.namespace,
                              repo.name,
                            )}
                          >
                            {repo.namespace}/{repo.name}
                          </Link>
                        ) : (
                          <Link
                            to={getRepoDetailPath(
                              location.pathname,
                              repo.namespace,
                              repo.name,
                            )}
                          >
                            {repo.name}
                          </Link>
                        )}
                      </FlexItem>
                    </Flex>
                  </Td>
                  <Td dataLabel={RepositoryListColumnNames.visibility}>
                    {repo.is_public ? 'public' : 'private'}
                  </Td>
                  {quayConfig?.features.QUOTA_MANAGEMENT &&
                  quayConfig?.features.EDIT_QUOTA ? (
                    <Td dataLabel={RepositoryListColumnNames.size}>
                      {(() => {
                        const sizeDisplay =
                          repo.size != null ? formatSize(repo.size) : '';

                        if (repo.configured_quota) {
                          const percentage =
                            repo.size != null
                              ? Math.round(
                                  (repo.size / repo.configured_quota) * 100,
                                )
                              : 0;

                          // Combine size and percentage: "1.5 GiB (45%)" or "N/A (0%)"
                          const displaySize = sizeDisplay || 'N/A';
                          return `${displaySize} (${percentage}%)`;
                        }

                        // No configured quota - just show size or empty
                        return sizeDisplay;
                      })()}
                    </Td>
                  ) : (
                    <></>
                  )}
                  <Td dataLabel={RepositoryListColumnNames.lastModified}>
                    {formatDate(repo.last_modified)}
                  </Td>
                </Tr>
              ))
            )}
          </Tbody>
        </Table>
        <PanelFooter>
          <ToolbarPagination {...paginationProps} bottom={true} />
        </PanelFooter>
      </PageSection>
    </>
  );
}

export interface RepoListTableItem {
  namespace: string;
  name: string;
  is_public: boolean;
  size: number;
  last_modified?: number;
  configured_quota?: number;
}

interface RepositoriesListProps {
  organizationName: string;
}
