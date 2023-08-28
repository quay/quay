import {useMutation, useQueryClient} from '@tanstack/react-query';
import {
  bulkDeleteRepoPermsForRobot,
  bulkUpdateRepoPermsForRobot,
  IRepoPerm,
} from 'src/resources/RobotsResource';
import {useState} from 'react';
import {useOrganizations} from 'src/hooks/UseOrganizations';

export function useRobotRepoPermissions({namespace, onSuccess, onError}) {
  const queryClient = useQueryClient();
  const [robotName, setRobotName] = useState('');

  const {usernames} = useOrganizations();
  const isUser = usernames.includes(namespace);

  const deleteRepoPermsMutator = useMutation(
    async ({robotName, repoNames}: bulkDeleteRepoPermsParams) => {
      setRobotName(robotName);
      return await bulkDeleteRepoPermsForRobot(
        namespace,
        robotName,
        repoNames,
        isUser,
      );
    },
    {
      onSuccess: (result) => {
        queryClient.invalidateQueries(['Namespace', namespace, 'robots']);
        queryClient.invalidateQueries([
          'Namespace',
          namespace,
          'robot',
          `${namespace}+${result.robotname}`,
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
    async ({robotName, repoPerms}: bulkUpdateRepoPermsParams) => {
      setRobotName(robotName);
      return await bulkUpdateRepoPermsForRobot(
        namespace,
        robotName,
        repoPerms,
        isUser,
      );
    },
    {
      onSuccess: (result) => {
        queryClient.invalidateQueries(['Namespace', namespace, 'robots']);
        queryClient.invalidateQueries([
          'Namespace',
          namespace,
          'robot',
          `${namespace}+${result.robotname}`,
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
    deleteRepoPerms: async (params: bulkDeleteRepoPermsParams) =>
      deleteRepoPermsMutator.mutate(params),
    updateRepoPerms: async (params: bulkUpdateRepoPermsParams) =>
      updateRepoPermsMutator.mutate(params),
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
