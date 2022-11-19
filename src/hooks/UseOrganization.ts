import {fetchOrg} from 'src/resources/OrganizationResource';
import {useQuery} from '@tanstack/react-query';
import {useOrganizations} from './UseOrganizations';
import {IOrganization} from 'src/resources/OrganizationResource';

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
    placeholderData: (): IOrganization[] => new Array(10).fill({}),
  });

  return {
    isUserOrganization,
    error,
    loading: isLoading,
    organization,
  };
}
