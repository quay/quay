import {fetchOrg, updateOrgSettings} from 'src/resources/OrganizationResource';
import {useMutation, useQuery} from '@tanstack/react-query';
import {useOrganizations} from './UseOrganizations';

export function useOrganization(name: string) {
  // Get usernames
  const {usernames} = useOrganizations();
  const isUserOrganization = usernames.includes(name);

  // Get organization
  const {
    data: organization,
    isLoading,
    error,
  } = useQuery(['organization', name], ({signal}) => fetchOrg(name, signal), {
    enabled: !isUserOrganization,
  });

  const updateOrgSettingsMutator = useMutation(
    async ({
      namespace,
      tag_expiration_s,
      email,
      isUser,
    }: updateOrgSettingsParams):Promise<Response> => {
      return await updateOrgSettings(
        namespace,
        tag_expiration_s,
        email,
        isUser,
      );
    },
  );

  return {
    isUserOrganization,
    error,
    loading: isLoading,
    organization,
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