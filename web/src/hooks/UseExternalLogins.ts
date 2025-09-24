import {useState, useEffect} from 'react';
import {useQuayConfig} from './UseQuayConfig';

export interface ExternalLoginProvider {
  id: string;
  title: string;
  icon: string;
  url?: string;
}

export function useExternalLogins() {
  const [externalLogins, setExternalLogins] = useState<ExternalLoginProvider[]>(
    [],
  );
  const quayConfig = useQuayConfig();

  useEffect(() => {
    if (quayConfig?.external_login) {
      setExternalLogins(quayConfig.external_login);
    }
  }, [quayConfig]);

  const hasExternalLogins = () => {
    return externalLogins.length > 0;
  };

  const hasSingleSignin = () => {
    return externalLogins.length === 1 && !quayConfig?.features?.DIRECT_LOGIN;
  };

  const shouldShowDirectLogin = () => {
    if (!quayConfig) return true;
    return (
      quayConfig.features?.DIRECT_LOGIN === true &&
      quayConfig.config?.AUTHENTICATION_TYPE !== 'OIDC'
    );
  };

  const shouldAutoRedirectSSO = () => {
    return hasSingleSignin();
  };

  const shouldShowExternalLoginsTab = () => {
    return !hasSingleSignin() && quayConfig?.registry_state !== 'readonly';
  };

  return {
    externalLogins,
    hasExternalLogins,
    hasSingleSignin,
    shouldShowDirectLogin,
    shouldAutoRedirectSSO,
    shouldShowExternalLoginsTab,
  };
}
