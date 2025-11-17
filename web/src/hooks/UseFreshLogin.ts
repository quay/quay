import {useState, useCallback} from 'react';
import axios from 'src/libs/axios';
import {AxiosResponse, AxiosError} from 'axios';
import {assertHttpCode} from 'src/resources/ErrorHandling';
import {useQuayConfig} from './UseQuayConfig';

interface VerifyUserRequest {
  password: string;
}

interface VerifyUserResponse {
  success: boolean;
}

interface FreshLoginState {
  isModalOpen: boolean;
  isLoading: boolean;
  error: string | null;
  pendingOperations: (() => Promise<void>)[];
}

async function verifyUser(password: string): Promise<void> {
  const response: AxiosResponse<VerifyUserResponse> = await axios.post(
    '/api/v1/signin/verify',
    {password} as VerifyUserRequest,
  );
  assertHttpCode(response.status, 200);
}

export function useFreshLogin() {
  const quayConfig = useQuayConfig();
  const [state, setState] = useState<FreshLoginState>({
    isModalOpen: false,
    isLoading: false,
    error: null,
    pendingOperations: [],
  });

  const showFreshLoginModal = useCallback(
    (retryOperation: () => Promise<void>) => {
      // Check if authentication type is OIDC
      if (quayConfig?.config?.AUTHENTICATION_TYPE === 'OIDC') {
        // For OIDC, redirect to re-authentication instead of showing password modal
        // Pass current URL as redirect_url parameter to return after re-auth
        const currentUrl = encodeURIComponent(window.location.href);
        window.location.href = `/signin?redirect_url=${currentUrl}`;
        return;
      }

      // For Database/LDAP authentication, show the password modal
      setState((prevState) => ({
        ...prevState,
        isModalOpen: true,
        error: null,
        pendingOperations: [...prevState.pendingOperations, retryOperation],
      }));
    },
    [quayConfig],
  );

  const handleVerify = useCallback(
    async (password: string) => {
      setState((prevState) => ({
        ...prevState,
        isLoading: true,
        error: null,
      }));

      try {
        await verifyUser(password);

        // On success, retry all pending operations
        const {pendingOperations} = state;
        setState({
          isModalOpen: false,
          isLoading: false,
          error: null,
          pendingOperations: [],
        });

        // Execute all pending operations
        for (const operation of pendingOperations) {
          try {
            await operation();
          } catch (error) {
            console.error(
              'Failed to retry operation after fresh login:',
              error,
            );
          }
        }
      } catch (error: unknown) {
        const axiosError = error as AxiosError;
        const errorMessage =
          ((axiosError?.response?.data as Record<string, unknown>)
            ?.message as string) || 'Invalid verification credentials';
        setState((prevState) => ({
          ...prevState,
          isLoading: false,
          error: errorMessage,
        }));
        throw error; // Re-throw so the modal can handle it
      }
    },
    [state.pendingOperations],
  );

  const handleCancel = useCallback(() => {
    setState({
      isModalOpen: false,
      isLoading: false,
      error: null,
      pendingOperations: [],
    });
  }, []);

  const isFreshLoginRequired = useCallback((error: unknown): boolean => {
    const axiosError = error as AxiosError;
    if (axiosError?.response?.status !== 401) return false;

    const data = axiosError.response?.data as Record<string, unknown>;
    return (
      data?.title === 'fresh_login_required' ||
      data?.error_type === 'fresh_login_required'
    );
  }, []);

  return {
    isModalOpen: state.isModalOpen,
    isLoading: state.isLoading,
    error: state.error,
    showFreshLoginModal,
    handleVerify,
    handleCancel,
    isFreshLoginRequired,
  };
}
