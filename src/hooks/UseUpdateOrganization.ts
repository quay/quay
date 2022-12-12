import {useMutation, useQueryClient} from '@tanstack/react-query';
import {updateOrg, UpdateOrgRequest} from 'src/resources/OrganizationResource';
export function useUpdateOrganization({onSuccess, onError}) {
  const queryClient = useQueryClient();

  const updateOrganizationMutator = useMutation(
    async ({
      name,
      updateOrgRequest,
    }: {
      name: string;
      updateOrgRequest: UpdateOrgRequest;
    }) => {
      return updateOrg(name, updateOrgRequest);
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
    updateOrganization: async (
      name: string,
      updateOrgRequest: UpdateOrgRequest,
    ) => updateOrganizationMutator.mutate({name, updateOrgRequest}),
    loading: updateOrganizationMutator.isLoading,
    error: updateOrganizationMutator.error,
  };
}
