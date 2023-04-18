import {useState} from 'react';
import {useMutation, useQuery, useQueryClient} from '@tanstack/react-query';
import {
  addDefaultPermsForRobot,
  createNewRobotForNamespace,
  fetchRobotsForNamespace,
  updateRepoPermsForRobot,
  IRobotRepoPerms,
  IRobotTeam,
} from 'src/resources/RobotsResource';
import {updateTeamForRobot} from 'src/resources/TeamResources';

export function useRobotAccounts({name, onSuccess, onError}) {
  const [page, setPage] = useState(1);
  const [perPage, setPerPage] = useState(10);
  const [namespace, setNamespace] = useState(name);

  const {
    data: robotAccountsForOrg,
    isLoading: loading,
    error,
  } = useQuery(
    ['Namespace', namespace, 'robots'],
    ({signal}) => fetchRobotsForNamespace(namespace, false, signal),
    {
      placeholderData: [],
      onSuccess: () => {
        onSuccess();
      },
      onError: (err) => {
        onError(err);
      },
    },
  );

  const queryClient = useQueryClient();

  const createRobotAccountMutator = useMutation(
    async ({
      namespace,
      robotname,
      description,
      isUser,
      reposToUpdate,
      selectedTeams,
      robotDefaultPerm,
    }: createNewRobotForNamespaceParams) => {
      return createNewRobotForNamespace(
        namespace,
        robotname,
        description,
        isUser,
        reposToUpdate,
        selectedTeams,
        robotDefaultPerm,
      );
    },
    {
      onSuccess: (result) => {
        if (result.reposToUpdate) {
          Promise.allSettled(
            result.reposToUpdate.map((repo) =>
              updateRepoPermsForRobot(
                namespace,
                result.robotname,
                repo.name,
                repo.permission,
                result.isUser,
              ),
            ),
          );
        }

        if (result.selectedTeams) {
          Promise.allSettled(
            result.selectedTeams.map((team) =>
              updateTeamForRobot(namespace, team.name, result.robotname),
            ),
          );
        }

        if (result.robotDefaultPerm && result.robotDefaultPerm != 'None') {
          addDefaultPermsForRobot(
            namespace,
            result.robotname,
            result.robotDefaultPerm,
          );
        }

        queryClient.invalidateQueries(['Namespace', namespace, 'robots']);
      },
    },
  );

  const addDefaultPermsForRobotMutator = useMutation(
    async ({
      namespace,
      robotname,
      permission,
    }: addDefaultPermsForRobotParams) => {
      return addDefaultPermsForRobot(namespace, robotname, permission);
    },
    {
      onSuccess: () => {
        queryClient.invalidateQueries(['Namespace', namespace, 'robots']);
      },
    },
  );

  const updateRepoPermsForRobotMutator = useMutation(
    async ({
      namespace,
      robotname,
      reponame,
      permission,
      isUser,
    }: updateRobotRepoPermsParams) => {
      return updateRepoPermsForRobot(
        namespace,
        robotname,
        reponame,
        permission,
        isUser,
      );
    },
    {
      onSuccess: () => {
        queryClient.invalidateQueries(['Namespace', namespace, 'robots']);
      },
    },
  );

  const updateTeamsForRobotMutator = useMutation(
    async ({namespace, teamname, robotname}: updateTeamsForRobotParams) => {
      return updateTeamForRobot(namespace, teamname, robotname);
    },
    {
      onSuccess: () => {
        queryClient.invalidateQueries(['organization', namespace, 'teams']);
      },
    },
  );

  return {
    robotAccountsForOrg: robotAccountsForOrg,
    loading: loading,
    error,
    setPage,
    setPerPage,
    page,
    perPage,
    setNamespace,
    namespace,
    createNewRobot: async (params: createNewRobotForNamespaceParams) =>
      createRobotAccountMutator.mutate(params),
    updateRepoPermsForRobot: async (params: updateRobotRepoPermsParams) =>
      updateRepoPermsForRobotMutator.mutate(params),
    updateTeamsForRobot: async (params: updateTeamsForRobotParams) =>
      updateTeamsForRobotMutator.mutate(params),
    addDefaultPermsForRobot: async (params: addDefaultPermsForRobotParams) =>
      addDefaultPermsForRobotMutator.mutate(params),
  };
}

interface createNewRobotForNamespaceParams {
  namespace: string;
  robotname: string;
  description: string;
  isUser?: boolean;
  reposToUpdate: IRobotRepoPerms[];
  selectedTeams: IRobotTeam[];
  robotDefaultPerm: string;
}

interface updateRobotRepoPermsParams {
  namespace: string;
  robotname: string;
  reponame: string;
  permission: string;
  isUser?: boolean;
}

interface updateTeamsForRobotParams {
  namespace: string;
  teamname: string;
  robotname: string;
}

interface addDefaultPermsForRobotParams {
  namespace: string;
  robotname: string;
  permission: string;
}
