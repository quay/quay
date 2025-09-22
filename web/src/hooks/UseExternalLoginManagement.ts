import {useQuery} from '@tanstack/react-query';
import {useExternalLogins} from './UseExternalLogins';
import {useExternalLoginAuth} from './UseExternalLoginAuth';

interface ExternalLoginInfo {
  service: string;
  metadata: {
    service_username?: string;
  };
}

interface User {
  logins?: Array<{
    service: string;
    metadata?: {
      service_username?: string;
    };
  }>;
}

export function useExternalLoginManagement() {
  const {externalLogins} = useExternalLogins();
  const {detachExternalLogin} = useExternalLoginAuth();

  // For now, mock the user data - in real implementation this would come from user context
  const user: User = {logins: []};

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
