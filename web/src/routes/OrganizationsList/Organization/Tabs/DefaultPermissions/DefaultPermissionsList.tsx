import {
  PageSection,
  PageSectionVariants,
  TextContent,
  Text,
  TextVariants,
  Spinner,
  Dropdown,
  MenuToggleElement,
  MenuToggle,
  DropdownItem,
  DropdownList,
} from '@patternfly/react-core';
import {
  Table,
  Tbody,
  Td,
  Th,
  Thead,
  Tr,
} from '../../../../../components/QuayTable';
import {useState} from 'react';
import {
  IDefaultPermission,
  useBulkDeleteDefaultPermissions,
  useFetchDefaultPermissions,
} from 'src/hooks/UseDefaultPermissions';
import DefaultPermissionsDropDown from './DefaultPermissionsDropDown';
import DefaultPermissionsToolbar from './DefaultPermissionsToolbar';
import DeleteDefaultPermissionKebab from './DeleteDefaultPermissionKebab';
import {BulkDeleteModalTemplate} from 'src/components/modals/BulkDeleteModalTemplate';
import Conditional from 'src/components/empty/Conditional';
import {BulkOperationError, addDisplayError} from 'src/resources/ErrorHandling';
import RequestError from 'src/components/errors/RequestError';
import {useAlerts} from 'src/hooks/UseAlerts';
import {AlertVariant} from 'src/atoms/AlertState';
import ErrorModal from 'src/components/errors/ErrorModal';
import {usePaginatedSortableTable} from '../../../../../hooks/usePaginatedSortableTable';

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
    errorLoadingPermissions,
    defaultPermissions,
    search,
    setSearch,
  } = useFetchDefaultPermissions(props.orgName);

  const searchFilter =
    search.query !== ''
      ? (permission: IDefaultPermission) =>
          permission.createdBy.includes(search.query)
      : undefined;

  const {
    paginatedData: paginatedPermissions,
    filteredData: filteredPermissions,
    getSortableSort,
    paginationProps,
  } = usePaginatedSortableTable(defaultPermissions || [], {
    columns: {
      1: (item: IDefaultPermission) => item.createdBy, // Repository Created By
      2: (item: IDefaultPermission) => item.appliedTo, // Permission Applied To
      3: (item: IDefaultPermission) => item.permission, // Permission
    },
    filter: searchFilter,
    initialPerPage: 20,
    initialSort: {columnIndex: 1, direction: 'asc'}, // Default sort: Repository Created By ascending
  });

  const [selectedPermissions, setSelectedPermissions] = useState<
    IDefaultPermission[]
  >([]);
  const [bulkDeleteModalIsOpen, setBulkDeleteModalIsOpen] = useState(false);
  const [err, setError] = useState<string[]>();
  const {addAlert} = useAlerts();

  const onSelectPermission = (
    permission: IDefaultPermission,
    rowIndex: number,
    isSelecting: boolean,
  ) => {
    setSelectedPermissions((prevSelected) => {
      const otherSelectedPermissions = prevSelected.filter(
        (p) => p.id !== permission.id,
      );
      return isSelecting
        ? [...otherSelectedPermissions, permission]
        : otherSelectedPermissions;
    });
  };

  const mapOfColNamesToTableData = {
    'Repository Created By': {
      label: 'createdBy',
      transformFunc: (perm: IDefaultPermission) => {
        return `${perm.createdBy}`;
      },
    },
    'Permission Applied To': {
      label: 'appliedTo',
      transformFunc: (perm: IDefaultPermission) => perm.appliedTo,
    },
    Permission: {
      label: 'permission',
      transformFunc: (perm: IDefaultPermission) => (
        <Dropdown
          toggle={(toggleRef: React.Ref<MenuToggleElement>) => (
            <MenuToggle ref={toggleRef} id="toggle-disabled" isDisabled>
              {perm.permission}
            </MenuToggle>
          )}
          isOpen={false}
        >
          <DropdownList>
            <DropdownItem>{perm.permission}</DropdownItem>
          </DropdownList>
        </Dropdown>
      ),
    },
  };

  const {bulkDeleteDefaultPermissions} = useBulkDeleteDefaultPermissions({
    orgName: props.orgName,
    onSuccess: () => {
      setBulkDeleteModalIsOpen(!bulkDeleteModalIsOpen);
      setSelectedPermissions([]);
      addAlert({
        variant: AlertVariant.Success,
        title: `Successfully deleted default permissions`,
      });
    },
    onError: (err) => {
      if (err instanceof BulkOperationError) {
        const errMessages = [];
        err.getErrors().forEach((error, perm) => {
          addAlert({
            variant: AlertVariant.Failure,
            title: `Could not delete  default permission for ${perm}: ${error.error}`,
          });
          errMessages.push(
            addDisplayError(
              `Failed to delete default permission created by: ${perm}`,
              error.error,
            ),
          );
        });
        setError(errMessages);
      } else {
        setError([addDisplayError('Failed to delete default permission', err)]);
      }
      setBulkDeleteModalIsOpen(!bulkDeleteModalIsOpen);
      setSelectedPermissions([]);
    },
  });

  const handleBulkDeleteModalToggle = () => {
    setBulkDeleteModalIsOpen(!bulkDeleteModalIsOpen);
  };

  if (loading) {
    return <Spinner />;
  }

  if (errorLoadingPermissions) {
    return (
      <>
        <RequestError message={'Unable to load default permissions list'} />
      </>
    );
  }

  return (
    <>
      <PageSection variant={PageSectionVariants.light}>
        <ErrorModal
          title="Default permission deletion failed"
          error={err}
          setError={setError}
        />
        <TextContent>
          <Text component={TextVariants.p}>
            The Default permissions panel defines permissions that should be
            granted automatically to a repository when it is created, in
            addition to the default of the repository&apos;s creator.
            Permissions are assigned based on the user who created the
            repository.
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
          page={paginationProps.page}
          setPage={paginationProps.setPage}
          perPage={paginationProps.perPage}
          setPerPage={paginationProps.setPerPage}
          search={search}
          setSearch={setSearch}
          searchOptions={[permissionColumnNames.repoCreatedBy]}
          setDrawerContent={props.setDrawerContent}
          handleBulkDeleteModalToggle={handleBulkDeleteModalToggle}
        >
          <Conditional if={bulkDeleteModalIsOpen}>
            <BulkDeleteModalTemplate
              mapOfColNamesToTableData={mapOfColNamesToTableData}
              handleModalToggle={handleBulkDeleteModalToggle}
              handleBulkDeletion={bulkDeleteDefaultPermissions}
              isModalOpen={bulkDeleteModalIsOpen}
              selectedItems={defaultPermissions?.filter((perm) =>
                selectedPermissions.some((selected) => perm.id === selected.id),
              )}
              resourceName={'default permissions'}
            />
          </Conditional>
          <Table
            aria-label="Selectable table"
            data-testid="default-permissions-table"
            variant="compact"
          >
            <Thead>
              <Tr>
                <Th />
                <Th sort={getSortableSort(1)}>
                  {permissionColumnNames.repoCreatedBy}
                </Th>
                <Th sort={getSortableSort(2)}>
                  {permissionColumnNames.permAppliedTo}
                </Th>
                <Th sort={getSortableSort(3)}>
                  {permissionColumnNames.permission}
                </Th>
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
                        (p) => p.id === permission.id,
                      ),
                    }}
                  />
                  <Td dataLabel={permissionColumnNames.repoCreatedBy}>
                    {permission.createdBy}
                  </Td>
                  <Td dataLabel={permissionColumnNames.permAppliedTo}>
                    {permission.appliedTo}
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
    </>
  );
}

interface DefaultPermissionsListProps {
  setDrawerContent: (any) => void;
  orgName: string;
}
