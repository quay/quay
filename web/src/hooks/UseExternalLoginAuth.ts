import {useState, useCallback} from 'react';
import axios from 'src/libs/axios';
import {addDisplayError} from 'src/resources/ErrorHandling';
import {ExternalLoginProvider} from './UseExternalLogins';
import {useQuayConfig} from './UseQuayConfig';

export function useExternalLoginAuth() {
  const [isAuthenticating, setIsAuthenticating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const quayConfig = useQuayConfig();

  const getAuthorizationUrl = useCallback(
    async (
      provider: ExternalLoginProvider,
      action: string = 'login',
    ): Promise<string> => {
      try {
        const response = await axios.post(
          `/api/v1/externallogin/${provider.id}`,
          {
            kind: action,
          },
        );
        return response.data.auth_url;
      } catch (err) {
        throw new Error(
          addDisplayError(
            'Could not load external login service information. Please contact your service administrator.',
            err,
          ),
        );
      }
    },
    [],
  );

  const startExternalLogin = useCallback(
    async (provider: ExternalLoginProvider, redirectUrl?: string) => {
      setIsAuthenticating(true);
      setError(null);

      try {
        const authUrl = await getAuthorizationUrl(provider, 'login');

        const finalRedirectUrl = redirectUrl || window.location.toString();
        localStorage.setItem('quay.redirectAfterLoad', finalRedirectUrl);

        setTimeout(() => {
          window.location.href = authUrl;
        }, 250);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Authentication failed');
        setIsAuthenticating(false);
      }
    },
    [getAuthorizationUrl],
  );

  const detachExternalLogin = useCallback(
    async (providerId: string) => {
      if (!quayConfig?.features?.DIRECT_LOGIN) {
        return;
      }

      try {
        await axios.post(`/api/v1/detachexternal/${providerId}`);
      } catch (err) {
        throw new Error(addDisplayError('Could not detach service', err));
      }
    },
    [quayConfig?.features?.DIRECT_LOGIN],
  );

  return {
    isAuthenticating,
    error,
    startExternalLogin,
    detachExternalLogin,
    getAuthorizationUrl,
  };
}
