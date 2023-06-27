import {useMutation, useQueryClient} from '@tanstack/react-query';
import {bulkDeleteOrganizations} from 'src/resources/OrganizationResource';
import {useQuayConfig} from './UseQuayConfig';
import {useEffect, useState} from "react";

export function useDeleteOrganizations({onSuccess, onError}) {
  const queryClient = useQueryClient();
  const quayConfig = useQuayConfig();
  const [isSuperUser, setSuperUser] = useState(false);

  useEffect(() => {
    setSuperUser(quayConfig?.features?.SUPERUSERS_FULL_ACCESS);
  })

  const deleteOrganizationsMutator = useMutation(
    async (orgs: string[]) => {
      await bulkDeleteOrganizations(orgs, isSuperUser);
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
