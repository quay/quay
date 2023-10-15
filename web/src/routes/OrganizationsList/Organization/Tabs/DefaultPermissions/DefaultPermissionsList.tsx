import {
  PageSection,
  PageSectionVariants,
  TextContent,
  Text,
  TextVariants,
  Spinner,
} from '@patternfly/react-core';
import {Table, Tbody, Td, Th, Thead, Tr} from '@patternfly/react-table';
import {useState} from 'react';
import {
  IDefaultPermission,
  useFetchDefaultPermissions,
} from 'src/hooks/UseDefaultPermissions';
import DefaultPermissionsDropDown from './DefaultPermissionsDropDown';
import DefaultPermissionsToolbar from './DefaultPermissionsToolbar';
import DeleteDefaultPermissionKebab from './DeleteDefaultPermissionKebab';
import {Link} from 'react-router-dom';

export const permissionColumnNames = {
  repoCreatedBy: 'Repository Created By',
  permAppliedTo: 'Permission Applied To',
  permission: 'Permission',
};

export enum repoPermissions {
  ADMIN = 'Admin',
  READ = 'Read',
  WRITE = 'Write',
}

export default function DefaultPermissionsList(
  props: DefaultPermissionsListProps,
) {
  const {
    loading,
    error,
    defaultPermissions,
    paginatedPermissions,
    filteredPermissions,
    page,
    setPage,
    perPage,
    setPerPage,
    search,
    setSearch,
  } = useFetchDefaultPermissions(props.orgName);

  const [selectedPermissions, setSelectedPermissions] = useState<
    IDefaultPermission[]
  >([]);

  const onSelectPermission = (
    permission: IDefaultPermission,
    rowIndex: number,
    isSelecting: boolean,
  ) => {
    setSelectedPermissions((prevSelected) => {
      const otherSelectedPermissions = prevSelected.filter(
        (p) => p.createdBy !== permission.createdBy,
      );
      return isSelecting
        ? [...otherSelectedPermissions, permission]
        : otherSelectedPermissions;
    });
  };

  if (loading) {
    return <Spinner />;
  }

  if (error) {
    return <>Unable to load default permissions list</>;
  }

  return (
    <PageSection variant={PageSectionVariants.light}>
      <TextContent>
        <Text component={TextVariants.p}>
          The Default permissions panel defines permissions that should be
          granted automatically to a repository when it is created, in addition
          to the default of the repository&apos;s creator. Permissions are
          assigned based on the user who created the repository.
        </Text>
        <Text component={TextVariants.p}>
          Note: Permissions added here do not automatically get added to
          existing repositories.
        </Text>
      </TextContent>
      <DefaultPermissionsToolbar
        selectedItems={selectedPermissions}
        deSelectAll={() => setSelectedPermissions([])}
        allItems={filteredPermissions}
        paginatedItems={paginatedPermissions}
        onItemSelect={onSelectPermission}
        page={page}
        setPage={setPage}
        perPage={perPage}
        setPerPage={setPerPage}
        search={search}
        setSearch={setSearch}
        searchOptions={[permissionColumnNames.repoCreatedBy]}
        setDrawerContent={props.setDrawerContent}
      >
        <Table
          aria-label="Selectable table"
          data-testid="default-permissions-table"
          variant="compact"
        >
          <Thead>
            <Tr>
              <Th />
              <Th>{permissionColumnNames.repoCreatedBy}</Th>
              <Th>{permissionColumnNames.permAppliedTo}</Th>
              <Th>{permissionColumnNames.permission}</Th>
              <Th />
            </Tr>
          </Thead>
          <Tbody>
            {paginatedPermissions?.map((permission, rowIndex) => (
              <Tr key={rowIndex}>
                <Td
                  select={{
                    rowIndex,
                    onSelect: (_event, isSelecting) =>
                      onSelectPermission(permission, rowIndex, isSelecting),
                    isSelected: selectedPermissions.some(
                      (p) => p.createdBy === permission.createdBy,
                    ),
                  }}
                />
                <Td dataLabel={permissionColumnNames.repoCreatedBy}>
                  <Link to="#">{permission.createdBy}</Link>
                </Td>
                <Td dataLabel={permissionColumnNames.permAppliedTo}>
                  <Link to="#">{permission.appliedTo}</Link>
                </Td>
                <Td dataLabel={permissionColumnNames.permission}>
                  <DefaultPermissionsDropDown
                    orgName={props.orgName}
                    defaultPermission={permission}
                  />
                </Td>
                <Td data-label="kebab">
                  <DeleteDefaultPermissionKebab
                    orgName={props.orgName}
                    defaultPermission={permission}
                  />
                </Td>
              </Tr>
            ))}
          </Tbody>
        </Table>
      </DefaultPermissionsToolbar>
    </PageSection>
  );
}

interface DefaultPermissionsListProps {
  setDrawerContent: (any) => void;
  orgName: string;
}
