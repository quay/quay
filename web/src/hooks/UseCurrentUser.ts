import {fetchUser} from 'src/resources/UserResource';
import {useQuery} from '@tanstack/react-query';
import {useQuayConfig} from './UseQuayConfig';

export function useCurrentUser() {
  const config = useQuayConfig();
  const {
    data: user,
    isLoading: loading,
    error,
  } = useQuery(['user'], fetchUser, {
    staleTime: Infinity,
  });

  const isSuperUser =
    config?.features?.SUPERUSERS_FULL_ACCESS && user?.super_user;

  return {user, loading, error, isSuperUser};
}
