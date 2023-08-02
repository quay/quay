import {useMutation, useQueryClient} from '@tanstack/react-query';
import {IRobot, bulkDeleteRobotAccounts} from 'src/resources/RobotsResource';

export function useDeleteRobotAccounts({namespace, onSuccess, onError}) {
  const queryClient = useQueryClient();

  const deleteRobotAccountsMutator = useMutation(
    async (robotacounts: IRobot[]) => {
      await bulkDeleteRobotAccounts(namespace, robotacounts);
    },
    {
      onSuccess: () => {
        queryClient.invalidateQueries(['Namespace', namespace, 'robots']);
        onSuccess();
      },
      onError: (err) => {
        onError(err);
      },
    },
  );

  return {
    // Mutations
    deleteRobotAccounts: async (robotacounts: IRobot[]) =>
      deleteRobotAccountsMutator.mutate(robotacounts),
  };
}
