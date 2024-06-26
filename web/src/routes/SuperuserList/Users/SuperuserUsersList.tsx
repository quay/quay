import {useEffect, useState} from 'react';
import {
  PageSection,
  PageSectionVariants,
  PanelFooter,
  Title,
} from '@patternfly/react-core';
import {QuayBreadcrumb} from 'src/components/breadcrumb/Breadcrumb';
import {Table, Thead, Tr, Th, Tbody, Td} from '@patternfly/react-table';
import ErrorModal from 'src/components/errors/ErrorModal';
import {ToolbarPagination} from 'src/components/toolbar/ToolbarPagination';
import {SuperuserUsersToolBar} from './SuperuserUsersToolBar';
import {
  ISuperuserUsers,
  useFetchSuperuserUsers,
} from 'src/hooks/UseSuperuserUsers';
import {SuperuserCreateUserModal} from '../SuperuserCreateUserModal';

export const superuserUsersViewColumnNames = {
  username: 'Username',
};

function SuperuserListHeader() {
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

export default function SuperuserUsersList(props: SuperuserListProps) {
  const [isUserModalOpen, setUserModalOpen] = useState(false);
  const [err, setErr] = useState<string[]>();
  const [selectedUsers, setSelectedUsers] = useState<ISuperuserUsers[]>([]);

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

  return (
    <>
      <SuperuserListHeader />
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
        <Table aria-label="Selectable table" variant="compact">
          <Thead>
            <Tr>
              <Th />
              <Th>{superuserUsersViewColumnNames.username}</Th>
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
                  dataLabel={superuserUsersViewColumnNames.username}
                  data-testid={`username-${user.username}`}
                >
                  {user.username}
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

interface SuperuserListProps {}
