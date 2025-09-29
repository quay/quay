import {useState, useCallback} from 'react';
import {useQueryClient} from '@tanstack/react-query';
import axios from 'src/libs/axios';
import {addDisplayError} from 'src/resources/ErrorHandling';
import {ExternalLoginProvider} from './UseExternalLogins';
import {useQuayConfig} from './UseQuayConfig';

export function useExternalLoginAuth() {
  const [isAuthenticating, setIsAuthenticating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const quayConfig = useQuayConfig();
  const queryClient = useQueryClient();

  const getAuthorizationUrl = useCallback(
    async (
      provider: ExternalLoginProvider,
      action = 'login',
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
        // Try to extract meaningful error message from response
        let errorMessage = 'Could not load external login service information';

        if (axios.isAxiosError(err) && err.response?.data?.error_message) {
          errorMessage = err.response.data.error_message;
        } else if (axios.isAxiosError(err) && err.response?.data?.message) {
          errorMessage = err.response.data.message;
        }

        throw new Error(errorMessage);
      }
    },
    [],
  );

  const startExternalLogin = useCallback(
    async (
      provider: ExternalLoginProvider,
      redirectUrl?: string,
      action?: string,
    ) => {
      setIsAuthenticating(true);
      setError(null);

      try {
        const authUrl = await getAuthorizationUrl(provider, action || 'login');

        const finalRedirectUrl = redirectUrl || window.location.toString();
        localStorage.setItem('quay.redirectAfterLoad', finalRedirectUrl);

        setTimeout(() => {
          window.location.href = authUrl;
        }, 250);
      } catch (err) {
        let errorMessage = 'Authentication failed';

        if (err instanceof Error) {
          errorMessage = err.message;
        } else if (typeof err === 'string') {
          errorMessage = err;
        }

        // More specific error messages for common scenarios
        if (errorMessage.includes('Network Error')) {
          errorMessage =
            'Unable to connect to authentication service. Please try again.';
        } else if (errorMessage.includes('timeout')) {
          errorMessage = 'Authentication request timed out. Please try again.';
        }

        setError(errorMessage);
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
        queryClient.invalidateQueries(['user']);
      } catch (err) {
        throw new Error(addDisplayError('Could not detach service', err));
      }
    },
    [quayConfig?.features?.DIRECT_LOGIN, queryClient],
  );

  return {
    isAuthenticating,
    error,
    startExternalLogin,
    detachExternalLogin,
    getAuthorizationUrl,
  };
}
