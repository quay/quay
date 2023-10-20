import {useState} from 'react';
import {
  updateOrgSettings,
  updateOrgSettingsParams,
} from 'src/resources/OrganizationResource';
import {useMutation, useQueryClient} from '@tanstack/react-query';

export function useOrganizationSettings({name, onSuccess, onError}) {
  const queryClient = useQueryClient();

  const updateOrgSettingsMutator = useMutation(
    async (params: Partial<updateOrgSettingsParams>): Promise<Response> => {
      return await updateOrgSettings(name, params);
    },
    {
      onSuccess: (result) => {
        queryClient.invalidateQueries(['organization', name]);
        queryClient.invalidateQueries(['user']);
        onSuccess(result);
      },
      onError: (err) => {
        onError(err);
      },
    },
  );

  return {
    updateOrgSettings: async (params: Partial<updateOrgSettingsParams>) =>
      updateOrgSettingsMutator.mutate(params),
  };
}
