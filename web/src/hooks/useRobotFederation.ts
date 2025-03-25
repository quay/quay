import {useMutation, useQuery, useQueryClient} from '@tanstack/react-query';
import {
  createRobotFederationConfig,
  fetchRobotFederationConfig,
  IRobotFederationConfig,
} from 'src/resources/RobotsResource';

export function useRobotFederation({namespace, robotName, onSuccess, onError}) {
  const queryClient = useQueryClient();

  const {
    data: robotFederationConfig,
    isLoading,
    error,
  } = useQuery(
    ['Namespace', namespace, 'robot', robotName, 'federation'],
    ({signal}) => fetchRobotFederationConfig(namespace, robotName, signal),
  );

  const robotFederationMutator = useMutation(
    async (args: CreateRobotFederationParams) => {
      return createRobotFederationConfig(
        args.namespace,
        args.robotName,
        args.config,
      );
    },
    {
      onSuccess: (result: IRobotFederationConfig[]) => {
        queryClient.invalidateQueries([
          'Namespace',
          namespace,
          'robot',
          robotName,
          'federation',
        ]);
        onSuccess(result);
      },
      onError: (createError) => {
        onError(createError?.response?.data);
      },
    },
  );

  return {
    robotFederationConfig,
    loading: isLoading,
    fetchError: error,

    // mutations
    setRobotFederationConfig: robotFederationMutator.mutate,
  };
}

interface CreateRobotFederationParams {
  namespace: string;
  robotName: string;
  config: IRobotFederationConfig[];
}
