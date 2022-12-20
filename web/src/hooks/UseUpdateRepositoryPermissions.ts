import {useMutation, useQueryClient} from '@tanstack/react-query';
import {
  bulkDeleteRepoPermissions,
  bulkSetRepoPermissions,
  RepoMember,
  RepoRole,
} from 'src/resources/RepositoryResource';

export function useUpdateRepositoryPermissions(org: string, repo: string) {
  const queryClient = useQueryClient();
  const {
    mutate: setPermissions,
    isError: errorSetPermissions,
    isSuccess: successSetPermissions,
    reset: resetSetRepoPermissions,
  } = useMutation(
    async ({
      members,
      newRole,
    }: {
      members: RepoMember[] | RepoMember;
      newRole: RepoRole;
    }) => {
      members = Array.isArray(members) ? members : [members];
      return bulkSetRepoPermissions(members, newRole);
    },
    {
      onSuccess: (_, variables) => {
        queryClient.invalidateQueries(['teamrepopermissions']);
        queryClient.invalidateQueries(['userrepopermissions']);
      },
    },
  );

  const {
    mutate: deletePermissions,
    isError: errorDeletePermissions,
    isSuccess: successDeletePermissions,
    reset: resetDeleteRepoPermissions,
  } = useMutation(
    async (members: RepoMember[] | RepoMember) => {
      members = Array.isArray(members) ? members : [members];
      return bulkDeleteRepoPermissions(members);
    },
    {
      onSuccess: (_, variables) => {
        queryClient.invalidateQueries(['teamrepopermissions']);
        queryClient.invalidateQueries(['userrepopermissions']);
      },
    },
  );

  return {
    setPermissions: setPermissions,
    errorSetPermissions: errorSetPermissions,
    successSetPermissions: successSetPermissions,
    resetSetRepoPermissions: resetSetRepoPermissions,

    deletePermissions: deletePermissions,
    errorDeletePermissions: errorDeletePermissions,
    successDeletePermissions: successDeletePermissions,
    resetDeleteRepoPermissions: resetDeleteRepoPermissions,
  };
}
