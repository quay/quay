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

  const updateRobotData = async (result) => {
    if (result.reposToUpdate) {
      await Promise.allSettled(
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
      await Promise.allSettled(
        result.selectedTeams.map((team) =>
          updateTeamForRobot(namespace, team.name, result.robotname),
        ),
      );
    }

    if (result.robotDefaultPerm && result.robotDefaultPerm != 'None') {
      await addDefaultPermsForRobot(
        namespace,
        result.robotname,
        result.robotDefaultPerm,
      );
    }
  };

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
      onSuccess: async (result) => {
        await Promise.allSettled([updateRobotData(result)]);
        queryClient.invalidateQueries(['Namespace', namespace, 'robots']);
        queryClient.invalidateQueries(['organization', namespace, 'teams']);
      },
      onError: (err) => {
        onError(err);
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
