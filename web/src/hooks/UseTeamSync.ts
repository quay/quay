import {useMutation, useQueryClient} from '@tanstack/react-query';
import {
  enableTeamSyncForOrg,
  removeTeamSyncForOrg,
} from 'src/resources/TeamSyncResource';
import {addDisplayError} from 'src/resources/ErrorHandling';

export function useTeamSync({orgName, teamName, onSuccess, onError}) {
  const queryClient = useQueryClient();

  const enableTeamSyncMutator = useMutation(
    async ({groupName, service}: {groupName: string; service: string}) => {
      return enableTeamSyncForOrg(orgName, teamName, groupName, service);
    },
    {
      onSuccess: (response) => {
        onSuccess(`Successfully updated team sync config`);
        queryClient.invalidateQueries(['teamMembers']);
        queryClient.invalidateQueries(['teams']);
      },
      onError: (err) => {
        onError(addDisplayError('Error updating team sync config', err));
      },
    },
  );

  return {
    enableTeamSync: async (groupName: string, service: string) =>
      enableTeamSyncMutator.mutate({groupName, service}),
  };
}

export function useRemoveTeamSync({orgName, teamName, onSuccess, onError}) {
  const queryClient = useQueryClient();

  const removeTeamSyncMutator = useMutation(
    async () => {
      return removeTeamSyncForOrg(orgName, teamName);
    },
    {
      onSuccess: () => {
        onSuccess(`Successfully removed team synchronization`);
        queryClient.invalidateQueries(['teamMembers']);
        queryClient.invalidateQueries(['teams']);
      },
      onError: (err) => {
        onError(addDisplayError('Error removing team synchronization', err));
      },
    },
  );

  return {
    removeTeamSync: async () => removeTeamSyncMutator.mutate(),
  };
}
