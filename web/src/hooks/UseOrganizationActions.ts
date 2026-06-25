import {useMutation, useQueryClient} from '@tanstack/react-query';
import {useNavigate} from 'react-router-dom';
import {
  deleteOrg,
  renameOrganization,
  takeOwnership,
} from 'src/resources/OrganizationResource';

export function useRenameOrganization({onSuccess, onError}) {
  const queryClient = useQueryClient();

  const renameOrganizationMutator = useMutation(
    async ({orgName, newName}: {orgName: string; newName: string}) => {
      return await renameOrganization(orgName, newName);
    },
    {
      onSuccess: (data, variables) => {
        // Invalidate the main organizations list queries
        queryClient.invalidateQueries([
          'organization',
          'superuser',
          'organizations',
        ]);
        queryClient.invalidateQueries(['organization', 'superuser', 'users']);
        queryClient.invalidateQueries(['user']);
        onSuccess(variables.orgName, variables.newName);
      },
      onError: (err) => {
        onError(err);
      },
    },
  );

  return {
    renameOrganization: async (orgName: string, newName: string) =>
      renameOrganizationMutator.mutate({orgName, newName}),
    isLoading: renameOrganizationMutator.isLoading,
  };
}

export function useDeleteSingleOrganization({onSuccess, onError}) {
  const queryClient = useQueryClient();

  const deleteOrganizationMutator = useMutation(
    async (orgName: string) => {
      return await deleteOrg(orgName, true); // true for superuser
    },
    {
      onSuccess: () => {
        // Invalidate the main organizations list queries
        queryClient.invalidateQueries([
          'organization',
          'superuser',
          'organizations',
        ]);
        queryClient.invalidateQueries(['organization', 'superuser', 'users']);
        queryClient.invalidateQueries(['user']);
        onSuccess();
      },
      onError: (err) => {
        onError(err);
      },
    },
  );

  return {
    deleteOrganization: async (orgName: string) =>
      deleteOrganizationMutator.mutate(orgName),
    isLoading: deleteOrganizationMutator.isLoading,
  };
}

export function useTakeOwnership({onSuccess, onError}) {
  const queryClient = useQueryClient();
  const navigate = useNavigate();

  const takeOwnershipMutator = useMutation(
    async (namespace: string) => {
      return await takeOwnership(namespace);
    },
    {
      onSuccess: (data, namespace) => {
        // Invalidate the main organizations list queries
        queryClient.invalidateQueries([
          'organization',
          'superuser',
          'organizations',
        ]);
        queryClient.invalidateQueries(['organization', 'superuser', 'users']);
        queryClient.invalidateQueries(['user']);
        // Navigate to the organization page
        navigate(`/organization/${namespace}`);
        onSuccess();
      },
      onError: (err) => {
        onError(err);
      },
    },
  );

  return {
    takeOwnership: async (namespace: string) =>
      takeOwnershipMutator.mutate(namespace),
    isLoading: takeOwnershipMutator.isLoading,
  };
}
