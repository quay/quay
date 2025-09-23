import {useMutation, useQueryClient} from '@tanstack/react-query';
import {deleteUser} from 'src/resources/UserResource';
import {deleteOrg} from 'src/resources/OrganizationResource';

export function useDeleteAccount({onSuccess, onError}) {
  const queryClient = useQueryClient();

  const deleteUserMutator = useMutation(
    async () => {
      return deleteUser();
    },
    {
      onSuccess: () => {
        onSuccess();
        // Clear all cache since user account is deleted
        queryClient.clear();
        // Redirect to signin would typically happen in the onSuccess callback
      },
      onError: (err) => {
        onError(err);
      },
    },
  );

  const deleteOrgMutator = useMutation(
    async (orgName: string) => {
      return deleteOrg(orgName);
    },
    {
      onSuccess: () => {
        onSuccess();
        queryClient.invalidateQueries(['user']);
        queryClient.invalidateQueries(['organization']);
      },
      onError: (err) => {
        onError(err);
      },
    },
  );

  return {
    deleteUser: async () => deleteUserMutator.mutateAsync(),
    deleteOrg: async (orgName: string) => deleteOrgMutator.mutateAsync(orgName),
    loading: deleteUserMutator.isLoading || deleteOrgMutator.isLoading,
    error: deleteUserMutator.error || deleteOrgMutator.error,
  };
}
