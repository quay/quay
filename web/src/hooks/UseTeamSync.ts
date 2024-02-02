import {useMutation, useQueryClient} from '@tanstack/react-query';
import {enableTeamSyncForOrg} from 'src/resources/TeamSyncResource';

export function useTeamSync({orgName, teamName, onSuccess, onError}) {
  const queryClient = useQueryClient();

  const enableTeamSyncMutator = useMutation(
    async ({groupName, service}: {groupName: string; service: string}) => {
      return enableTeamSyncForOrg(orgName, teamName, groupName, service);
    },
    {
      onSuccess: () => {
        onSuccess();
        queryClient.invalidateQueries([orgName, teamName, 'teamSync']);
      },
      onError: (err) => {
        onError(err);
      },
    },
  );
  return {
    enableTeamSync: async (groupName: string, service: string) =>
      enableTeamSyncMutator.mutate({groupName, service}),
  };
}
