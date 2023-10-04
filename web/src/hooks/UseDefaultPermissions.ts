import {useMutation, useQuery, useQueryClient} from '@tanstack/react-query';
import {useState} from 'react';
import {SearchState} from 'src/components/toolbar/SearchTypes';
import {
  bulkDeleteDefaultPermissions,
  createDefaultPermission,
  deleteDefaultPermission,
  fetchDefaultPermissions,
  updateDefaultPermission,
} from 'src/resources/DefaultPermissionResource';
import {Entity} from 'src/resources/UserResource';
import {permissionColumnNames} from 'src/routes/OrganizationsList/Organization/Tabs/DefaultPermissions/DefaultPermissionsList';

export interface IDefaultPermission {
  createdBy: string;
  appliedTo: string;
  permission: string;
  id?: string;
}

export interface IPrototype {
  activating_user?: {
    name: string;
  };
  delegate: {
    name: string;
  };
  role: string;
  id?: string;
}

interface createDefaultPermissionParams {
  repoCreator?: Entity;
  appliedTo: Entity;
  newRole: string;
}

export function useFetchDefaultPermissions(org: string) {
  const [page, setPage] = useState(1);
  const [perPage, setPerPage] = useState(20);
  const [search, setSearch] = useState<SearchState>({
    query: '',
    field: permissionColumnNames.repoCreatedBy,
  });

  const {
    data: permissions,
    isError: errorLoadingPermissions,
    isLoading: loadingPermissions,
    isPlaceholderData,
  } = useQuery<IPrototype[]>(
    ['defaultpermissions', org],
    () => fetchDefaultPermissions(org),
    {
      placeholderData: [],
    },
  );

  const defaultPermissions: IDefaultPermission[] = [];
  permissions?.map((perm) => {
    defaultPermissions.push({
      createdBy: perm.activating_user
        ? perm.activating_user.name
        : 'organization default',
      appliedTo: perm.delegate.name,
      permission: perm.role,
      id: perm.id,
    });
  });

  const filteredPermissions =
    search.query !== ''
      ? defaultPermissions?.filter((permission) =>
          permission.createdBy.includes(search.query),
        )
      : defaultPermissions;

  const paginatedPermissions = filteredPermissions?.slice(
    page * perPage - perPage,
    page * perPage - perPage + perPage,
  );

  return {
    loading: loadingPermissions || isPlaceholderData,
    errorLoadingPermissions,
    defaultPermissions,
    paginatedPermissions,
    filteredPermissions,
    page,
    setPage,
    perPage,
    setPerPage,
    search,
    setSearch,
  };
}

export function useUpdateDefaultPermission(org: string) {
  const queryClient = useQueryClient();
  const {
    mutate: setDefaultPermission,
    isError: errorSetDefaultPermission,
    isSuccess: successSetDefaultPermission,
    reset: resetSetDefaultPermission,
  } = useMutation(
    async ({id, newRole}: {id: string; newRole: string}) => {
      return updateDefaultPermission(org, id, newRole);
    },
    {
      onSuccess: (_, variables) => {
        queryClient.invalidateQueries(['defaultpermissions']);
      },
    },
  );
  return {
    setDefaultPermission,
    errorSetDefaultPermission,
    successSetDefaultPermission,
    resetSetDefaultPermission,
  };
}

export function useDeleteDefaultPermission(org: string) {
  const queryClient = useQueryClient();
  const {
    mutate: removeDefaultPermission,
    isError: errorDeleteDefaultPermission,
    isSuccess: successDeleteDefaultPermission,
    reset: resetDeleteDefaultPermission,
  } = useMutation(
    async ({perm}: {perm: IDefaultPermission}) => {
      return deleteDefaultPermission(org, perm);
    },
    {
      onSuccess: () => {
        queryClient.invalidateQueries(['defaultpermissions']);
      },
    },
  );
  return {
    removeDefaultPermission,
    errorDeleteDefaultPermission,
    successDeleteDefaultPermission,
    resetDeleteDefaultPermission,
  };
}

export function useCreateDefaultPermission(orgName, {onError, onSuccess}) {
  const queryClient = useQueryClient();

  const createDefaultPermissionMutator = useMutation(
    async ({
      repoCreator,
      appliedTo,
      newRole,
    }: createDefaultPermissionParams) => {
      const permissionData = {
        delegate: {
          name: appliedTo.name,
          kind: appliedTo.kind,
          is_robot: appliedTo.is_robot,
          ...(appliedTo?.is_org_member !== undefined && {
            is_org_member: appliedTo.is_org_member,
          }),
        },
        role: newRole,
      };
      if (repoCreator) {
        permissionData['activating_user'] = {
          name: repoCreator.name,
          kind: repoCreator.kind,
          is_robot: repoCreator.is_robot,
          is_org_member: repoCreator.is_org_member,
        };
      }
      return createDefaultPermission(orgName, permissionData);
    },
    {
      onSuccess: () => {
        onSuccess();
        queryClient.invalidateQueries(['defaultpermissions']);
      },
      onError: () => {
        onError();
      },
    },
  );

  return {
    createDefaultPermission: async (params: createDefaultPermissionParams) =>
      createDefaultPermissionMutator.mutate(params),
  };
}

export function useBulkDeleteDefaultPermissions({orgName, onSuccess, onError}) {
  const queryClient = useQueryClient();

  const bulkDeleteDefaultPermissionsMutator = useMutation(
    async (perms: IDefaultPermission[]) => {
      return bulkDeleteDefaultPermissions(orgName, perms);
    },
    {
      onSuccess: () => {
        queryClient.invalidateQueries(['defaultpermissions']);
        onSuccess();
      },
      onError: (err) => {
        onError(err);
      },
    },
  );

  return {
    // Mutations
    bulkDeleteDefaultPermissions: async (perms: IDefaultPermission[]) =>
      bulkDeleteDefaultPermissionsMutator.mutate(perms),
  };
}
