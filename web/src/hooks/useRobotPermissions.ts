import {
  bulkDeleteRepoPermsForRobot,
  bulkUpdateRepoPermsForRobot,
  fetchRobotPermissionsForNamespace,
  IRepoPerm,
} from 'src/resources/RobotsResource';
import {useMutation, useQuery, useQueryClient} from '@tanstack/react-query';
import {useState} from 'react';

export function useRobotPermissions({orgName, robName, onSuccess, onError}) {
  const [namespace, setNamespace] = useState(orgName);
  const [robotName, setRobotName] = useState(robName);
  const [page, setPage] = useState(1);
  const [perPage, setPerPage] = useState(10);

  const {
    data: robotPermissions,
    isLoading: loading,
    error,
  } = useQuery(
    ['Namespace', namespace, 'robot', robotName, 'permissions'],
    ({signal}) =>
      fetchRobotPermissionsForNamespace(namespace, robotName, false, signal),
    {
      enabled: true,
      placeholderData: [],
      onSuccess: (result) => {
        onSuccess(result);
      },
      onError: (err) => {
        onError(err);
      },
    },
  );

  const queryClient = useQueryClient();
  const deleteRepoPermsMutator = useMutation(
    async (repoNames: string[]) => {
      await bulkDeleteRepoPermsForRobot(namespace, robName, repoNames);
    },
    {
      onSuccess: () => {
        queryClient.invalidateQueries(['Namespace', namespace, 'robots']);
        queryClient.invalidateQueries([
          'Namespace',
          namespace,
          'robot',
          robotName,
          'permissions',
        ]);
        onSuccess();
      },
      onError: (err) => {
        onError(err);
      },
    },
  );

  const updateRepoPermsMutator = useMutation(
    async (repoPerms: IRepoPerm[]) => {
      return await bulkUpdateRepoPermsForRobot(namespace, robotName, repoPerms);
    },
    {
      onSuccess: () => {
        queryClient.invalidateQueries(['Namespace', namespace, 'robots']);
        queryClient.invalidateQueries([
          'Namespace',
          namespace,
          'robot',
          robotName,
          'permissions',
        ]);
        onSuccess();
      },
      onError: (err) => {
        onError(err);
      },
    },
  );

  return {
    result: robotPermissions,
    loading: loading,
    error,
    setPage,
    setPerPage,
    page,
    perPage,
    setNamespace,
    namespace,
    setRobotName,

    // Mutations
    updateRepoPerms: async (repoPerms: IRepoPerm[]) =>
      updateRepoPermsMutator.mutate(repoPerms),
    deleteRepoPerms: async (repoNames: string[]) =>
      deleteRepoPermsMutator.mutate(repoNames),
  };
}

interface bulkUpdateRepoPermsParams {
  robotName: string;
  repoPerms: IRepoPerm[];
}

interface bulkDeleteRepoPermsParams {
  robotName: string;
  repoNames: string[];
}
