import {ReactElement, useEffect, useState} from 'react';
import {
  PageSection,
  PageSectionVariants,
  Spinner,
  Title,
  PanelFooter,
  DropdownItem,
} from '@patternfly/react-core';
import {Table, Thead, Tr, Th, Tbody, Td} from '@patternfly/react-table';
import {useRecoilState} from 'recoil';
import {IRepository} from 'src/resources/RepositoryResource';
import {Link, useLocation} from 'react-router-dom';
import CreateRepositoryModalTemplate from 'src/components/modals/CreateRepoModalTemplate';
import {getRepoDetailPath} from 'src/routes/NavigationPath';
import {selectedReposState} from 'src/atoms/RepositoryState';
import {formatDate, formatSize} from 'src/libs/utils';
import {BulkDeleteModalTemplate} from 'src/components/modals/BulkDeleteModalTemplate';
import {RepositoryToolBar} from 'src/routes/RepositoriesList/RepositoryToolBar';
import {
  addDisplayError,
  BulkOperationError,
  isErrorString,
} from 'src/resources/ErrorHandling';
import RequestError from 'src/components/errors/RequestError';
import Empty from 'src/components/empty/Empty';
import {CubesIcon} from '@patternfly/react-icons';
import {ToolbarButton} from 'src/components/toolbar/ToolbarButton';
import {QuayBreadcrumb} from 'src/components/breadcrumb/Breadcrumb';
import ErrorModal from 'src/components/errors/ErrorModal';
import {useQuayConfig} from 'src/hooks/UseQuayConfig';
import {ToolbarPagination} from 'src/components/toolbar/ToolbarPagination';
import {RepositoryListColumnNames} from './ColumnNames';
import {LoadingPage} from 'src/components/LoadingPage';
import {useCurrentUser} from 'src/hooks/UseCurrentUser';
import {useRepositories} from 'src/hooks/UseRepositories';
import {useDeleteRepositories} from 'src/hooks/UseDeleteRepositories';

interface RepoListHeaderProps {
  shouldRender: boolean;
  title?: string;
}
function RepoListHeader(props: RepoListHeaderProps) {
  if (!props.shouldRender) {
    return null;
  }

  const title = props.title || 'Repositories';
  return (
    <>
      <QuayBreadcrumb />
      <PageSection variant={PageSectionVariants.light} hasShadowBottom>
        <div className="co-m-nav-title--row">
          <Title headingLevel="h1">{title}</Title>
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
  const repoKind = props.repoKind || 'image';

  const quayConfig = useQuayConfig();
  const {user} = useCurrentUser();
  const {
    repos,
    loading,
    error,
    setPerPage,
    setPage,
    search,
    setSearch,
    searchFilter,
    page,
    perPage,
    totalResults,
  } = useRepositories(currentOrg, repoKind);

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
    } as RepoListTableItem;
  });

  useEffect(() => {
    if (search.currentOrganization !== currentOrg) {
      setSearch({...search, query: '', currentOrganization: currentOrg});
    }
  }, [currentOrg]);

  // Filtering Repositories after applied filter
  const filteredRepos = searchFilter
    ? repositoryList.filter(searchFilter)
    : repositoryList;

  const paginatedRepositoryList = filteredRepos?.slice(
    page * perPage - perPage,
    page * perPage - perPage + perPage,
  );

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
      selectedItems={repositoryList.filter((repo) =>
        selectedRepoNames.some(
          (selected) => repo.namespace + '/' + repo.name === selected,
        ),
      )}
      resourceName={'repositories'}
    />
  );

  // Return component Loading state
  if (loading) {
    return (
      <>
        <RepoListHeader shouldRender={currentOrg === null} />
        <LoadingPage />
      </>
    );
  }

  // Return component Error state
  if (isErrorString(error as any)) {
    return (
      <>
        <RepoListHeader shouldRender={currentOrg === null} />
        <RequestError message={error as any} />
      </>
    );
  }

  // Return component Empty state
  if (!loading && !repositoryList?.length) {
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
      <RepoListHeader shouldRender={currentOrg === null} title={props.title} />
      <PageSection variant={PageSectionVariants.light}>
        <ErrorModal title="Org deletion failed" error={err} setError={setErr} />
        <RepositoryToolBar
          search={search}
          setSearch={setSearch}
          total={totalResults}
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
          perPage={perPage}
          page={page}
          setPage={setPage}
          setPerPage={setPerPage}
          setSelectedRepoNames={setSelectedRepoNames}
          paginatedRepositoryList={paginatedRepositoryList}
          onSelectRepo={onSelectRepo}
        />
        <Table aria-label="Selectable table" variant="compact">
          <Thead>
            <Tr>
              <Th />
              <Th>{RepositoryListColumnNames.name}</Th>
              <Th>{RepositoryListColumnNames.visibility}</Th>
              {quayConfig?.features.QUOTA_MANAGEMENT &&
              quayConfig?.features.EDIT_QUOTA ? (
                <Th>{RepositoryListColumnNames.size}</Th>
              ) : (
                <></>
              )}
              <Th>{RepositoryListColumnNames.lastModified}</Th>
            </Tr>
          </Thead>
          <Tbody data-testid="repository-list-table">
            {repositoryList.length === 0 ? (
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
                  </Td>
                  <Td dataLabel={RepositoryListColumnNames.visibility}>
                    {repo.is_public ? 'public' : 'private'}
                  </Td>
                  {quayConfig?.features.QUOTA_MANAGEMENT &&
                  quayConfig?.features.EDIT_QUOTA ? (
                    <Td dataLabel={RepositoryListColumnNames.size}>
                      {' '}
                      {formatSize(repo.size)}
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
          <ToolbarPagination
            total={totalResults}
            itemsList={filteredRepos}
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

export interface RepoListTableItem {
  namespace: string;
  name: string;
  is_public: boolean;
  size: number;
  last_modified: number;
}

interface RepositoriesListProps {
  organizationName: string;
  title?: string;
  repoKind?: string;
}
