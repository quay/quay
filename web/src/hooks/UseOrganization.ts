import {fetchOrg} from 'src/resources/OrganizationResource';
import {useQuery} from '@tanstack/react-query';
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

  return {
    isUserOrganization,
    error,
    loading: isLoading,
    organization,
  };
}
