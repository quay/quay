import {useMutation, useQueryClient} from '@tanstack/react-query';
import {createOrg} from 'src/resources/OrganizationResource';
export function useCreateOrganization({onSuccess, onError}) {
  const queryClient = useQueryClient();

  const createOrganizationMutator = useMutation(
    async ({name, email}: {name: string; email: string}) => {
      return createOrg(name, email);
    },
    {
      onSuccess: () => {
        onSuccess();
        queryClient.invalidateQueries(['user']);
      },
      onError: (err) => {
        onError(err);
      },
    },
  );

  return {
    createOrganization: async (name: string, email: string) =>
      createOrganizationMutator.mutate({name, email}),
  };
}
