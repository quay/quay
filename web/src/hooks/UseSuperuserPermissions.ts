import {useCurrentUser} from './UseCurrentUser';
import {useQuayState} from './UseQuayState';

/**
 * Hook for determining superuser permissions and capabilities.
 * Supports read-only superusers
 */
export function useSuperuserPermissions() {
  const {user} = useCurrentUser();
  const {inReadOnlyMode} = useQuayState();

  const isSuperUser = user?.super_user === true;
  const isReadOnlySuperUser = user?.global_readonly_super_user === true;

  // User can modify data if: superuser AND NOT read-only superuser AND registry NOT in read-only mode
  const canModify = isSuperUser && !isReadOnlySuperUser && !inReadOnlyMode;

  return {
    // True if user is any type of superuser (read-write or read-only)
    isSuperUser: isSuperUser || isReadOnlySuperUser,

    // True if user is specifically a read-only superuser
    isReadOnlySuperUser,

    // True if user can modify data (use to enable/disable actions)
    canModify,

    // True if registry is in read-only mode
    inReadOnlyMode,
  };
}
