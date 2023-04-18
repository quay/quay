import {
  DropdownItem,
  PageSection,
  PageSectionVariants,
  PanelFooter,
  Spinner,
  TextContent,
  Text,
  TextVariants,
} from '@patternfly/react-core';
import {
  TableComposable,
  ExpandableRowContent,
  Thead,
  Tr,
  Th,
  Tbody,
  Td,
} from '@patternfly/react-table';
import {Link} from 'react-router-dom';
import {RobotAccountColumnNames} from './ColumnNames';

import {RobotAccountsToolBar} from 'src/routes/RepositoriesList/RobotAccountsToolBar';
import CreateRobotAccountModal from 'src/components/modals/CreateRobotAccountModal';
import {IRobot} from 'src/resources/RobotsResource';
import {useRecoilState, useRecoilValue} from 'recoil';
import {
  searchRobotAccountState,
  selectedRobotAccountsState,
} from 'src/atoms/RobotAccountState';
import {useRobotAccounts} from 'src/hooks/useRobotAccounts';
import {ReactElement, useState, useRef, useEffect} from 'react';
import {ToolbarPagination} from 'src/components/toolbar/ToolbarPagination';
import RobotAccountKebab from './RobotAccountKebab';
import {useDeleteRobotAccounts} from 'src/hooks/UseDeleteRobotAccount';
import {BulkDeleteModalTemplate} from 'src/components/modals/BulkDeleteModalTemplate';
import {addDisplayError, BulkOperationError} from 'src/resources/ErrorHandling';
import ErrorModal from 'src/components/errors/ErrorModal';
import Empty from 'src/components/empty/Empty';
import {CubesIcon} from '@patternfly/react-icons';
import {ToolbarButton} from 'src/components/toolbar/ToolbarButton';
import {formatDate} from 'src/libs/utils';
import TeamView from 'src/components/modals/robotAccountWizard/TeamView';
import DisplayModal from 'src/components/modals/robotAccountWizard/DisplayModal';
import RobotRepositoryPermissions from 'src/components/modals/RobotRepositoryPermissions';
import {useQuery, useQueryClient} from '@tanstack/react-query';
import {fetchOrg} from 'src/resources/OrganizationResource';
import {
  selectedReposPermissionState,
  selectedReposState,
} from 'src/atoms/RepositoryState';
import {useRobotRepoPermissions} from 'src/hooks/UseRobotRepoPermissions';
import RobotTokensModal from 'src/components/modals/RobotTokensModal';

const RepoPermissionDropdownItems = [
  {
    name: 'None',
    description: 'No permissions on the repository',
  },
  {
    name: 'Read',
    description: 'Can view and pull from the repository',
  },
  {
    name: 'Write',
    description: 'Can view, pull, and push to the repository',
  },
  {
    name: 'Admin',
    description: 'Full admin access to the organization',
  },
];

const EmptyRobotAccount = {
  name: '',
  created: '',
  last_accessed: '',
  teams: [],
  repositories: [],
  description: '',
};

export default function RobotAccountsList(props: RobotAccountsListProps) {
  const search = useRecoilValue(searchRobotAccountState);
  const [selectedReposForModalView, setSelectedReposForModalView] =
    useRecoilState(selectedReposState);
  const [isCreateRobotModalOpen, setCreateRobotModalOpen] = useState(false);
  const [isKebabOpen, setKebabOpen] = useState(false);
  const [isDeleteModalOpen, setDeleteModalOpen] = useState(false);
  const [isTableExpanded, setTableExpanded] = useState(false);
  const [loading, setLoading] = useState<boolean>(true);
  const [isTeamsModalOpen, setTeamsModalOpen] = useState<boolean>(false);
  const [teamsViewItems, setTeamsViewItems] = useState([]);
  const [isReposModalOpen, setReposModalOpen] = useState<boolean>(false);
  const [robotRepos, setRobotRepos] = useState([]);
  const [teams, setTeams] = useState([]);
  const [robotForDeletion, setRobotForDeletion] = useState([]);
  const [robotForModalView, setRobotForModalView] = useState(EmptyRobotAccount);
  const [isTokenModalOpen, setTokenModalOpen] = useState<boolean>(false);
  // For repository modal view
  const [selectedRepoPerms, setSelectedRepoPerms] = useRecoilState(
    selectedReposPermissionState,
  );
  const [prevRepoPerms, setPrevRepoPerms] = useState({});
  const [showRepoModalSave, setShowRepoModalSave] = useState(false);
  const [newRepoPerms, setNewRepoPerms] = useState({});
  const [err, setErr] = useState<string[]>();
  const [errTitle, setErrTitle] = useState<string>();
  const robotPermissionsPlaceholder = useRef(null);

  const {robotAccountsForOrg, page, perPage, setPage, setPerPage} =
    useRobotAccounts({
      name: props.orgName,
      onSuccess: () => {
        setLoading(false);
      },
      onError: (err) => {
        setErrTitle('Failed to fetch Robot Accounts');
        setErr([addDisplayError('Unable to fetch robot accounts', err)]);
        setLoading(false);
      },
    });

  const queryClient = useQueryClient();

  const robotAccountsList: IRobot[] = robotAccountsForOrg?.map(
    (robotAccount) => {
      return {
        name: robotAccount.name,
        teams: robotAccount.teams,
        repositories: robotAccount.repositories,
        last_accessed: robotAccount.last_accessed,
        created: robotAccount.created,
        description: robotAccount.description,
      } as IRobot;
    },
  );

  // Fetching teams
  useQuery(
    ['organization', props.orgName, 'teams'],
    ({signal}) => {
      fetchOrg(props.orgName, signal).then((response) => {
        setTeams(Object['values'](response?.teams));
        return response?.teams;
      });
      return [];
    },
    {
      placeholderData: () => {
        return queryClient.getQueryData(['organization', props.orgName]);
      },
    },
  );

  const filteredRobotAccounts =
    search.query !== ''
      ? robotAccountsList.filter((robotAccount) => {
          const RobotAccountname = robotAccount.name;
          return RobotAccountname.includes(search.query);
        })
      : robotAccountsList;

  const paginatedRobotAccountList = filteredRobotAccounts?.slice(
    page * perPage - perPage,
    page * perPage - perPage + perPage,
  );

  // Expandable Row Logic
  const [expandedRobotNames, setExpandedRobotNames] = useState<string[]>([]);
  const setRobotExpanded = (robot: IRobot, isExpanding = true) =>
    setExpandedRobotNames((prevExpanded) => {
      const otherExpandedRepoNames = prevExpanded.filter(
        (r) => r !== robot.name,
      );
      return isExpanding
        ? [...otherExpandedRepoNames, robot.name]
        : otherExpandedRepoNames;
    });
  const isRobotExpanded = (robot) => expandedRobotNames.includes(robot.name);

  // Logic for handling row-wise checkbox selection in <Td>
  const isRobotAccountSelected = (rob: IRobot) =>
    selectedRobotAccounts.includes(rob.name);

  const [selectedRobotAccounts, setSelectedRobotAccounts] = useRecoilState(
    selectedRobotAccountsState,
  );

  const fetchBulKUpdateErrorMsg = (err, msg) => {
    const errMessages = [];
    err.getErrors().forEach((error, resource) => {
      errMessages.push(addDisplayError(`${msg} ${resource}`, error.error));
    });
    return errMessages;
  };

  const {deleteRobotAccounts} = useDeleteRobotAccounts({
    namespace: props.orgName,
    onSuccess: () => {
      setSelectedRobotAccounts([]);
      setDeleteModalOpen(!isDeleteModalOpen);
    },
    onError: (err) => {
      setErrTitle('Robot Account deletion failed');
      if (err instanceof BulkOperationError) {
        const errMessages = fetchBulKUpdateErrorMsg(
          err,
          `Failed to delete robot account`,
        );
        setErr(errMessages);
      } else {
        setErr([addDisplayError('Failed to delete robot account', err)]);
      }
      setSelectedRobotAccounts([]);
      setDeleteModalOpen(!isDeleteModalOpen);
    },
  });

  const {updateRepoPerms, deleteRepoPerms} = useRobotRepoPermissions({
    namespace: props.orgName,
    onSuccess: () => null,
    onError: (err) => {
      setErrTitle('Repository Permission update failed');
      if (err instanceof BulkOperationError) {
        const errMessages = fetchBulKUpdateErrorMsg(
          err,
          `Failed to update robot repository permission`,
        );
        setErr(errMessages);
      } else {
        setErr([
          addDisplayError('Failed to update robot repository permission', err),
        ]);
      }
    },
  });

  const setRobotAccountsSelected = (robotAccount: IRobot, isSelecting = true) =>
    setSelectedRobotAccounts((prevSelected) => {
      const otherSelectedRobotNames = prevSelected.filter(
        (r) => r !== robotAccount.name,
      );
      return isSelecting
        ? [...otherSelectedRobotNames, robotAccount.name]
        : otherSelectedRobotNames;
    });

  const isRobotAccountSelectable = (robot) => robot.name !== ''; // Arbitrary logic for this example

  const onSelectRobot = (
    robotAccount: IRobot,
    rowIndex: number,
    isSelecting: boolean,
  ) => {
    setRobotAccountsSelected(robotAccount, isSelecting);
  };

  const onReposModalClose = () => {
    setSelectedReposForModalView([]);
    setSelectedRepoPerms([]);
    robotPermissionsPlaceholder.current.resetRobotPermissions();
    setRobotForModalView(EmptyRobotAccount);
  };

  const onRepoModalSave = async () => {
    try {
      const robotname = robotForModalView.name.replace(props.orgName + '+', '');
      const [toUpdate, toDelete] = updateRepoPermissions();
      if (toUpdate.length > 0) {
        await updateRepoPerms({robotName: robotname, repoPerms: toUpdate});
      }
      if (toDelete.length > 0) {
        await deleteRepoPerms({robotName: robotname, repoNames: toDelete});
      }
    } catch (error) {
      console.error(error);
      setErr([
        addDisplayError('Failed to update robot repository permission', error),
      ]);
    }
  };

  const updateRepoPermissions = () => {
    const toUpdate = [];
    Object.keys(newRepoPerms).forEach((repo) => {
      if (
        newRepoPerms[repo]?.toLowerCase() != prevRepoPerms[repo]?.toLowerCase()
      ) {
        toUpdate.push({
          reponame: repo,
          permission: newRepoPerms[repo].toLowerCase(),
        });
      }
    });

    const toDelete = [];
    Object.keys(prevRepoPerms).forEach((repo) => {
      if (!(repo in newRepoPerms)) {
        toDelete.push(repo);
      }
    });
    return [toUpdate, toDelete];
  };

  const fetchReposModal = (robotAccount, repos) => {
    setRobotForModalView(robotAccount);
    setRobotRepos(repos);
    setReposModalOpen(true);
  };

  const fetchTeamsModal = (items) => {
    const filteredItems = teams.filter((team) =>
      items.some((item) => team.name === item.name),
    );
    setTeamsModalOpen(true);
    setTeamsViewItems(filteredItems);
  };

  const getLength = (robotAccount, list, teams) => {
    const len = list.length;
    let placeholder = 'teams';
    let single_placeholder = 'team';

    if (!teams) {
      placeholder = 'repositories';
      single_placeholder = 'repository';
    }

    if (len == 0 && teams) {
      return 'No ' + placeholder;
    }
    return (
      <Link
        to="#"
        onClick={() =>
          teams ? fetchTeamsModal(list) : fetchReposModal(robotAccount, list)
        }
      >
        {len > 0 ? len.toString() + ' ' : 'No '}
        {len == 1 ? single_placeholder : placeholder}
      </Link>
    );
  };

  const fetchTokensModal = (robotAccount) => {
    setTokenModalOpen(!isTokenModalOpen);
    setRobotForModalView(robotAccount);
  };

  const onTokenModalClose = () => {
    setRobotForModalView(EmptyRobotAccount);
  };

  const mapOfColNamesToTableData = {
    RobotAccount: {
      label: 'name',
      transformFunc: (item: string) => {
        return `${item}`;
      },
    },
  };

  const handleBulkDeleteModalToggle = () => {
    setKebabOpen(!isKebabOpen);
    setDeleteModalOpen(!isDeleteModalOpen);
    setRobotForDeletion([]);
  };

  const bulkDeleteRobotAccounts = async () => {
    const items =
      robotForDeletion.length > 0 ? robotForDeletion : selectedRobotAccounts;
    await deleteRobotAccounts(items);
    setRobotForDeletion([]);
  };

  const bulkDeleteRobotAccountModal = () => {
    const items =
      robotForDeletion.length > 0 ? robotForDeletion : selectedRobotAccounts;
    return (
      <BulkDeleteModalTemplate
        mapOfColNamesToTableData={mapOfColNamesToTableData}
        handleModalToggle={handleBulkDeleteModalToggle}
        handleBulkDeletion={bulkDeleteRobotAccounts}
        isModalOpen={isDeleteModalOpen}
        selectedItems={items}
        resourceName={'robot accounts'}
      />
    );
  };

  const kebabItems: ReactElement[] = [
    <DropdownItem
      key="delete-item"
      className="red-color"
      onClick={handleBulkDeleteModalToggle}
    >
      Delete
    </DropdownItem>,
  ];

  const createRobotModal = (
    <CreateRobotAccountModal
      isModalOpen={isCreateRobotModalOpen}
      handleModalToggle={() => setCreateRobotModalOpen(!isCreateRobotModalOpen)}
      namespace={props.orgName}
      teams={teams}
      RepoPermissionDropdownItems={RepoPermissionDropdownItems}
    />
  );

  const collapseTable = () => {
    setTableExpanded(!isTableExpanded);
    setExpandedRobotNames([]);
  };

  const expandTable = () => {
    if (isTableExpanded) {
      return;
    }
    setTableExpanded(!isTableExpanded);
    paginatedRobotAccountList.map((robotAccount, index) => {
      setRobotExpanded(robotAccount);
    });
  };

  if (!loading && !robotAccountsForOrg?.length) {
    return (
      <Empty
        title="There are no viewable robot accounts for this repository"
        icon={CubesIcon}
        body="Either no robot accounts exist yet or you may not have permission to view any. If you have the permissions, you may create robot accounts in this repository."
        button={
          <ToolbarButton
            id=""
            buttonValue="Create robot account"
            Modal={createRobotModal}
            isModalOpen={isCreateRobotModalOpen}
            setModalOpen={setCreateRobotModalOpen}
          />
        }
      />
    );
  }

  if (loading && paginatedRobotAccountList.length == 0) {
    return (
      <TableComposable aria-label="Empty state table" borders={false}>
        <Tbody>
          <Tr>
            <Td colSpan={8} textCenter={true}>
              <Spinner diameter="50px" />
            </Td>
          </Tr>
          <Tr>
            <Td colSpan={8} textCenter={true}>
              <TextContent>
                <Text component={TextVariants.h3}>Loading</Text>
              </TextContent>
            </Td>
          </Tr>
        </Tbody>
      </TableComposable>
    );
  }
  return (
    <>
      <PageSection variant={PageSectionVariants.light}>
        <ErrorModal title={errTitle} error={err} setError={setErr} />
        <RobotAccountsToolBar
          selectedItems={selectedRobotAccounts}
          allItemsList={filteredRobotAccounts}
          setSelectedRobotAccounts={setSelectedRobotAccounts}
          itemsPerPageList={paginatedRobotAccountList}
          onItemSelect={onSelectRobot}
          buttonText="Create robot account"
          pageModal={createRobotModal}
          isModalOpen={isCreateRobotModalOpen}
          setModalOpen={setCreateRobotModalOpen}
          isKebabOpen={isKebabOpen}
          setKebabOpen={setKebabOpen}
          kebabItems={kebabItems}
          deleteModal={bulkDeleteRobotAccountModal}
          deleteKebabIsOpen={isDeleteModalOpen}
          setDeleteModalOpen={setDeleteModalOpen}
          perPage={perPage}
          page={page}
          setPage={setPage}
          setPerPage={setPerPage}
          total={filteredRobotAccounts.length}
          expandTable={expandTable}
          collapseTable={collapseTable}
        />
        <DisplayModal
          isModalOpen={isTeamsModalOpen}
          setIsModalOpen={setTeamsModalOpen}
          title="Teams"
          showSave={false}
          Component={
            <TeamView
              items={teamsViewItems}
              showCheckbox={false}
              showToggleGroup={false}
              searchInputText="Search for team"
              filterWithDropdown={false}
            />
          }
        ></DisplayModal>
        <DisplayModal
          isModalOpen={isReposModalOpen}
          setIsModalOpen={setReposModalOpen}
          onClose={onReposModalClose}
          title="Set repository permissions"
          showSave={showRepoModalSave}
          onSave={onRepoModalSave}
          Component={
            <RobotRepositoryPermissions
              robotAccount={robotForModalView}
              namespace={props.orgName}
              RepoPermissionDropdownItems={RepoPermissionDropdownItems}
              repos={robotRepos}
              selectedRepos={selectedReposForModalView}
              setSelectedRepos={setSelectedReposForModalView}
              selectedRepoPerms={selectedRepoPerms}
              setSelectedRepoPerms={setSelectedRepoPerms}
              robotPermissionsPlaceholder={robotPermissionsPlaceholder}
              setPrevRepoPerms={setPrevRepoPerms}
              setNewRepoPerms={setNewRepoPerms}
              setShowRepoModalSave={setShowRepoModalSave}
            />
          }
        ></DisplayModal>
        <DisplayModal
          isModalOpen={isTokenModalOpen}
          setIsModalOpen={setTokenModalOpen}
          title={`Credentials for ${robotForModalView.name}`}
          showSave={false}
          onClose={onTokenModalClose}
          Component={
            <RobotTokensModal
              namespace={props.orgName}
              robotAccount={robotForModalView}
            />
          }
        />
        <TableComposable aria-label="Expandable table" variant={undefined}>
          <Thead>
            <Tr>
              <Th />
              <Th />
              <Th modifier="wrap">
                {RobotAccountColumnNames.robotAccountName}
              </Th>
              <Th modifier="wrap">{RobotAccountColumnNames.teams}</Th>
              <Th modifier="wrap">{RobotAccountColumnNames.repositories}</Th>
              <Th modifier="wrap">{RobotAccountColumnNames.lastAccessed}</Th>
              <Th modifier="wrap">{RobotAccountColumnNames.created}</Th>
              <Th />
            </Tr>
          </Thead>
          {paginatedRobotAccountList.map((robotAccount, rowIndex) => {
            return (
              <Tbody key={rowIndex} isExpanded={isRobotExpanded(robotAccount)}>
                <Tr>
                  <Td
                    expand={
                      robotAccount.description
                        ? {
                            rowIndex,
                            isExpanded: isRobotExpanded(robotAccount),
                            onToggle: () =>
                              setRobotExpanded(
                                robotAccount,
                                !isRobotExpanded(robotAccount),
                              ),
                          }
                        : undefined
                    }
                  />

                  <Td
                    select={{
                      rowIndex,
                      onSelect: (_event, isSelecting) =>
                        onSelectRobot(robotAccount, rowIndex, isSelecting),
                      isSelected: isRobotAccountSelected(robotAccount),
                      disable: !isRobotAccountSelectable(robotAccount),
                    }}
                  />
                  <Td dataLabel={RobotAccountColumnNames.robotAccountName}>
                    <Link to="#" onClick={() => fetchTokensModal(robotAccount)}>
                      {robotAccount.name}
                    </Link>
                  </Td>
                  <Td dataLabel={RobotAccountColumnNames.teams}>
                    {getLength(robotAccount, robotAccount.teams, true)}
                  </Td>
                  <Td dataLabel={RobotAccountColumnNames.repositories}>
                    {getLength(robotAccount, robotAccount.repositories, false)}
                  </Td>
                  <Td dataLabel={RobotAccountColumnNames.lastAccessed}>
                    {robotAccount.last_accessed
                      ? robotAccount.last_accessed
                      : 'Never'}
                  </Td>
                  <Td dataLabel={RobotAccountColumnNames.created}>
                    {formatDate(robotAccount.created)}
                  </Td>
                  <Td data-label="kebab">
                    <RobotAccountKebab
                      robotAccount={robotAccount}
                      namespace={props.orgName}
                      setError={setErr}
                      deleteModal={bulkDeleteRobotAccountModal}
                      deleteKebabIsOpen={isDeleteModalOpen}
                      setDeleteModalOpen={setDeleteModalOpen}
                      setSelectedRobotAccount={setRobotForDeletion}
                      onSetRepoPermsClick={fetchReposModal}
                      robotAccountRepos={robotAccount.repositories}
                    />
                  </Td>
                </Tr>
                {robotAccount.description ? (
                  <Tr isExpanded={isRobotExpanded(robotAccount)}>
                    <Td
                      dataLabel="Robot Account description"
                      noPadding={false}
                      colSpan={7}
                    >
                      <ExpandableRowContent>
                        {robotAccount.description}
                      </ExpandableRowContent>
                    </Td>
                  </Tr>
                ) : null}
              </Tbody>
            );
          })}
        </TableComposable>
        <PanelFooter>
          <ToolbarPagination
            itemsList={filteredRobotAccounts}
            perPage={perPage}
            page={page}
            setPage={setPage}
            setPerPage={setPerPage}
            bottom={true}
            total={filteredRobotAccounts.length}
          />
        </PanelFooter>
      </PageSection>
    </>
  );
}

interface RobotAccountsListProps {
  orgName: string;
}
