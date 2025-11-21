import {useExternalLogins} from './UseExternalLogins';
import {useExternalLoginAuth} from './UseExternalLoginAuth';
import {useCurrentUser} from './UseCurrentUser';

interface ExternalLoginInfo {
  service: string;
  metadata: {
    service_username?: string;
  };
}

export function useExternalLoginManagement() {
  const {externalLogins} = useExternalLogins();
  const {detachExternalLogin} = useExternalLoginAuth();
  const {user} = useCurrentUser();

  const userExternalLogins = user?.logins || [];

  const getExternalLoginInfo = () => {
    const loginInfo: Record<string, ExternalLoginInfo> = {};
    userExternalLogins.forEach((login) => {
      loginInfo[login.service] = {
        service: login.service,
        metadata: login.metadata || {},
      };
    });
    return loginInfo;
  };

  const isProviderAttached = (providerId: string) => {
    return userExternalLogins.some((login) => login.service === providerId);
  };

  return {
    externalLogins,
    externalLoginInfo: getExternalLoginInfo(),
    isProviderAttached,
    detachExternalLogin,
  };
}
