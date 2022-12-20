import {useMutation, useQueryClient} from '@tanstack/react-query';
import {bulkDeleteOrganizations} from 'src/resources/OrganizationResource';

export function useDeleteOrganizations({onSuccess, onError}) {
  const queryClient = useQueryClient();

  const deleteOrganizationsMutator = useMutation(
    async (orgs: string[]) => {
      await bulkDeleteOrganizations(orgs);
    },
    {
      onSuccess: () => {
        queryClient.invalidateQueries(['user']);
        onSuccess();
      },
      onError: (err) => {
        onError(err);
      },
    },
  );

  return {
    // Mutations
    deleteOrganizations: async (orgs: string[]) =>
      deleteOrganizationsMutator.mutate(orgs),
  };
}
