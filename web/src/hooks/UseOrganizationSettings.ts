import {useState} from 'react';
import {updateOrgSettings} from 'src/resources/OrganizationResource';
import {useMutation, useQueryClient} from '@tanstack/react-query';

export function useOrganizationSettings({name, onSuccess, onError}) {
  const queryClient = useQueryClient();

  const updateOrgSettingsMutator = useMutation(
    async ({
      namespace,
      tag_expiration_s,
      email,
      isUser,
    }: updateOrgSettingsParams): Promise<Response> => {
      return await updateOrgSettings(
        namespace,
        tag_expiration_s,
        email,
        isUser,
      );
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
    updateOrgSettings: async (params: updateOrgSettingsParams) =>
      updateOrgSettingsMutator.mutate(params),
  };
}

interface updateOrgSettingsParams {
  namespace: string;
  tag_expiration_s: number;
  email: string;
  isUser: boolean;
}