import {useState} from 'react';
import {useMutation, useQuery, useQueryClient} from '@tanstack/react-query';
import {
  addDefaultPermsForRobot,
  createNewRobotForNamespace,
  fetchRobotsForNamespace,
  updateRepoPermsForRobot,
  IRobotRepoPerms,
  IRobotTeam,
  IRobot,
  createRobotAccount,
  bulkDeleteRepoPermsForRobot,
  bulkUpdateRepoPermsForRobot,
  fetchRobotPermissionsForNamespace,
  IRepoPerm,
  fetchRobotAccountToken,
  regenerateRobotToken,
} from 'src/resources/RobotsResource';
import {updateTeamForRobot} from 'src/resources/TeamResources';
import {useOrganizations} from 'src/hooks/UseOrganizations';
import {isNullOrUndefined} from 'src/libs/utils';

export function useFetchRobotAccounts(
  orgName: string,
  isUser = false,
  enabled = true,
) {
  const {
    data: robots,
    isLoading,
    error,
    isError,
    isSuccess,
  } = useQuery<IRobot[]>(
    ['robots'],
    ({signal}) => fetchRobotsForNamespace(orgName, isUser, signal),
    {
      placeholderData: [],
      enabled: enabled,
    },
  );

  return {
    error,
    isLoadingRobots: isLoading,
    robots,
    isSuccess,
    isError,
  };
}

interface createNewRobotAccountForNamespaceParams {
  robotAccntName: string;
  description: string;
}

export function useCreateRobotAccount({namespace, onSuccess, onError}) {
  const queryClient = useQueryClient();

  const addRepoPermsMutator = useMutation(
    async ({
      namespace,
      robotname,
      isUser,
      reposToUpdate,
    }: addRepoPermsParams) => {
      return Promise.allSettled(
        reposToUpdate.map((repo) =>
          updateRepoPermsForRobot(
            namespace,
            robotname,
            repo.name,
            repo.permission,
            isUser,
          ),
        ),
      );
    },
    {
      onSuccess: async (result) => {
        queryClient.invalidateQueries(['Namespace', namespace, 'robots']);
      },
      onError: (err) => {
        onError('Error updating repository permissions for the robot account');
      },
    },
  );

  const addTeamsMutator = useMutation(
    async ({namespace, robotname, selectedTeams}: addTeamsParams) => {
      return Promise.allSettled(
        selectedTeams.map((team) =>
          updateTeamForRobot(namespace, team.name, robotname),
        ),
      );
    },
    {
      onSuccess: async (result) => {
        queryClient.invalidateQueries(['Namespace', namespace, 'robots']);
        queryClient.invalidateQueries(['organization', namespace, 'teams']);
        queryClient.invalidateQueries(['teamMembers']);
      },
      onError: (err) => {
        onError('Error updating teams for the robot account');
      },
    },
  );

  const addDefaultPermsMutator = useMutation(
    async ({namespace, robotname, robotDefaultPerm}: addDefaultPermsParams) => {
      return await addDefaultPermsForRobot(
        namespace,
        robotname,
        robotDefaultPerm,
      );
    },
    {
      onSuccess: async (result) => {
        queryClient.invalidateQueries(['Namespace', namespace, 'robots']);
      },
      onError: (err) => {
        onError('Error updating default permissions for the robot account');
      },
    },
  );

  const createRobotAccountMutator = useMutation(
    async ({
      namespace,
      robotname,
      description,
      isUser,
    }: createNewRobotForNamespaceParams) => {
      return createNewRobotForNamespace(
        namespace,
        robotname,
        description,
        isUser,
      );
    },
    {
      onSuccess: async (result) => {
        onSuccess(
          `Successfully created robot account with robot name: ${result['name']}`,
        );
        queryClient.invalidateQueries(['Namespace', namespace, 'robots']);
      },
      onError: (err) => {
        onError(err);
      },
    },
  );

  return {
    createNewRobot: async (params: createNewRobotForNamespaceParams) =>
      createRobotAccountMutator.mutateAsync(params),
    addRepoPerms: async (params: addRepoPermsParams) =>
      addRepoPermsMutator.mutateAsync(params),
    addTeams: async (params: addTeamsParams) =>
      addTeamsMutator.mutateAsync(params),
    addDefaultPerms: async (params: addDefaultPermsParams) =>
      addDefaultPermsMutator.mutateAsync(params),
  };
}

interface createNewRobotForNamespaceParams {
  namespace: string;
  robotname: string;
  description: string;
  isUser?: boolean;
}

interface addRepoPermsParams {
  namespace: string;
  robotname: string;
  reposToUpdate: IRobotRepoPerms[];
  isUser?: boolean;
}

interface addTeamsParams {
  namespace: string;
  robotname: string;
  selectedTeams: IRobotTeam[];
}

interface addDefaultPermsParams {
  namespace: string;
  robotname: string;
  robotDefaultPerm: string;
}

export function useRobotAccounts({name, onSuccess, onError, enabled}) {
  const [page, setPage] = useState(1);
  const [perPage, setPerPage] = useState(20);
  const [namespace, setNamespace] = useState(name);

  const {usernames} = useOrganizations();
  const isUser = usernames.includes(name);

  const {
    data: robotAccountsForOrg,
    isLoading: loading,
    isError,
    error,
  } = useQuery(
    ['Namespace', namespace, 'robots'],
    ({signal}) => fetchRobotsForNamespace(namespace, isUser, signal),
    {
      placeholderData: [],
      onSuccess: () => {
        onSuccess();
      },
      onError: (err) => {
        onError(err);
      },
      enabled: isNullOrUndefined(enabled) ? true : enabled,
    },
  );

  return {
    robotAccountsForOrg: robotAccountsForOrg,
    loading: loading,
    error,
    isError,
    setPage,
    setPerPage,
    page,
    perPage,
    setNamespace,
    namespace,
  };
}

export function useRobotPermissions({orgName, robotAcct, onSuccess, onError}) {
  const [namespace, setNamespace] = useState(orgName);
  const [robotName, setRobotName] = useState(robotAcct);
  const [page, setPage] = useState(1);
  const [perPage, setPerPage] = useState(20);

  const {usernames} = useOrganizations();
  const isUser = usernames.includes(orgName);

  const {
    data: robotPermissions,
    isLoading: loading,
    error,
  } = useQuery(
    ['Namespace', namespace, 'robot', robotName, 'permissions'],
    ({signal}) =>
      fetchRobotPermissionsForNamespace(namespace, robotName, isUser, signal),
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
      await bulkDeleteRepoPermsForRobot(
        namespace,
        robotAcct,
        repoNames,
        isUser,
      );
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
    loading,
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

export function useRobotToken({orgName, robotAcct, onSuccess, onError}) {
  const {usernames} = useOrganizations();
  const isUserOrganization = usernames.includes(orgName);
  const [namespace, setNamespace] = useState(orgName);
  const [robotName, setRobotName] = useState(robotAcct);
  const [page, setPage] = useState(1);
  const [perPage, setPerPage] = useState(20);
  const queryClient = useQueryClient();

  const {data: robotAccountToken, isLoading: loading} = useQuery(
    ['Namespace', namespace, 'robot', robotName, 'token'],
    ({signal}) =>
      fetchRobotAccountToken(namespace, robotName, isUserOrganization, signal),
    {
      enabled: true,
      placeholderData: {},
      onSuccess: (result) => {
        onSuccess(result);
      },
      onError: (err) => {
        onError(err);
      },
    },
  );

  const regenerateRobotTokenMutator = useMutation(
    async ({namespace, robotName}: regenerateRobotTokenParams) => {
      return regenerateRobotToken(namespace, robotName, isUserOrganization);
    },
    {
      onSuccess: (result) => {
        queryClient.invalidateQueries([
          'Namespace',
          namespace,
          'robot',
          robotName,
          'token',
        ]);
        onSuccess(result);
      },
      onError: (err) => {
        onError(err);
      },
    },
  );

  return {
    robotAccountToken: robotAccountToken,
    loading: loading,

    regenerateRobotToken: async (regenerateRobotTokenParams) =>
      regenerateRobotTokenMutator.mutate(regenerateRobotTokenParams),
  };
}

interface regenerateRobotTokenParams {
  namespace: string;
  robotName: string;
}
