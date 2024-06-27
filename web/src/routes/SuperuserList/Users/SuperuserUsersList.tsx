import {useState} from 'react';
import {
  PageSection,
  PageSectionVariants,
  PanelFooter,
  Spinner,
  Title,
} from '@patternfly/react-core';
import {QuayBreadcrumb} from 'src/components/breadcrumb/Breadcrumb';
import {Table, Thead, Tr, Th, Tbody, Td} from '@patternfly/react-table';
import ErrorModal from 'src/components/errors/ErrorModal';
import {ToolbarPagination} from 'src/components/toolbar/ToolbarPagination';
import {SuperuserUsersToolBar} from './SuperuserUsersToolBar';
import {
  ISuperuserUsers,
  useDeleteUser,
  useFetchSuperuserUsers,
} from 'src/hooks/UseSuperuserUsers';
import {SuperuserCreateUserModal} from '../SuperuserCreateUserModal';
import DeleteModalForRowTemplate from 'src/components/modals/DeleteModalForRowTemplate';
import Conditional from 'src/components/empty/Conditional';
import {useAlerts} from 'src/hooks/UseAlerts';
import {AlertVariant} from 'src/atoms/AlertState';
import UsersKebab from './SuperuserUsersKebab';

export const superuserUsersColumnNames = {
  username: 'Username',
};

function SuperuserUsersListHeader() {
  return (
    <>
      <QuayBreadcrumb />
      <PageSection variant={PageSectionVariants.light} hasShadowBottom>
        <div className="co-m-nav-title--row">
          <Title headingLevel="h1">Users</Title>
        </div>
      </PageSection>
    </>
  );
}

export default function SuperuserUsersList(props: SuperuserUsersListProps) {
  const [isUserModalOpen, setUserModalOpen] = useState(false);
  const [err, setErr] = useState<string[]>();
  const [selectedUsers, setSelectedUsers] = useState<ISuperuserUsers[]>([]);

  const [isDeleteModalForRowOpen, setIsDeleteModalForRowOpen] = useState(false);
  const [userToBeDeleted, setUserToBeDeleted] = useState<ISuperuserUsers>();
  const {addAlert} = useAlerts();

  const {
    users,
    paginatedUsers,
    filteredUsers,
    isLoadingUsers,
    errorLoadingUsers,
    page,
    setPage,
    perPage,
    setPerPage,
    search,
    setSearch,
  } = useFetchSuperuserUsers();

  const {removeUser} = useDeleteUser({
    onSuccess: () => {
      setIsDeleteModalForRowOpen(false);
      addAlert({
        variant: AlertVariant.Success,
        title: `Successfully deleted user: ${userToBeDeleted.username}`,
      });
    },
    onError: (err) => {
      addAlert({
        variant: AlertVariant.Failure,
        title: `Unable to delete user: ${userToBeDeleted.username}, ${err}`,
      });
    },
  });

  const onSelectUser = (
    user: ISuperuserUsers,
    rowIndex: number,
    isSelecting: boolean,
  ) => {
    setSelectedUsers((prevSelected) => {
      const otherSelectedUsers = prevSelected.filter(
        (t) => t.username !== user.username,
      );
      return isSelecting ? [...otherSelectedUsers, user] : otherSelectedUsers;
    });
  };

  const createUserModal = (
    <SuperuserCreateUserModal
      isModalOpen={isUserModalOpen}
      handleModalToggle={() => setUserModalOpen(!isUserModalOpen)}
    />
  );

  const deleteUserRowModal = (
    <DeleteModalForRowTemplate
      deleteMsgTitle={'Remove user'}
      isModalOpen={isDeleteModalForRowOpen}
      toggleModal={() => setIsDeleteModalForRowOpen(!isDeleteModalForRowOpen)}
      deleteHandler={removeUser}
      itemToBeDeleted={userToBeDeleted}
      keyToDisplay="name"
    />
  );

  if (isLoadingUsers) {
    return <Spinner />;
  }

  return (
    <>
      <SuperuserUsersListHeader />
      <ErrorModal title="User deletion failed" error={err} setError={setErr} />
      <PageSection variant={PageSectionVariants.light}>
        <SuperuserUsersToolBar
          selectedUsers={selectedUsers}
          deSelectAll={() => setSelectedUsers([])}
          allItems={filteredUsers}
          paginatedItems={paginatedUsers}
          onItemSelect={onSelectUser}
          search={search}
          setSearch={setSearch}
          createUserModal={createUserModal}
          isUserModalOpen={isUserModalOpen}
          setUserModalOpen={setUserModalOpen}
          perPage={perPage}
          page={page}
          setPage={setPage}
          setPerPage={setPerPage}
        />
        <Conditional if={isDeleteModalForRowOpen}>
          {deleteUserRowModal}
        </Conditional>
        <Table aria-label="Selectable table" variant="compact">
          <Thead>
            <Tr>
              <Th />
              <Th>{superuserUsersColumnNames.username}</Th>
            </Tr>
          </Thead>
          <Tbody>
            {paginatedUsers?.map((user, rowIndex) => (
              <Tr key={user.username}>
                <Td
                  select={{
                    rowIndex,
                    onSelect: (_event, isSelecting) =>
                      onSelectUser(user, rowIndex, isSelecting),
                    isSelected: selectedUsers.some(
                      (u) => u.username === user.username,
                    ),
                  }}
                />
                <Td
                  dataLabel={superuserUsersColumnNames.username}
                  data-testid={`username-${user.username}`}
                >
                  {user.username}
                </Td>
                <Td data-label="kebab">
                  <UsersKebab
                    user={user}
                    deSelectAll={() => setSelectedUsers([])}
                    onDeleteTeam={() => {
                      setUserToBeDeleted(user);
                      setIsDeleteModalForRowOpen(!isDeleteModalForRowOpen);
                    }}
                  />
                </Td>
              </Tr>
            ))}
          </Tbody>
        </Table>
        <PanelFooter>
          <ToolbarPagination
            itemsList={filteredUsers}
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

interface SuperuserUsersListProps {}
