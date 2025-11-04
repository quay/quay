import {useState, useCallback} from 'react';
import {getCsrfToken} from 'src/libs/axios';
import {AxiosError} from 'axios';
import {verifyUser} from 'src/resources/AuthResource';

interface FreshLoginState {
  isModalOpen: boolean;
  isLoading: boolean;
  error: string | null;
  pendingOperations: (() => Promise<void>)[];
}

export function useFreshLogin() {
  const [state, setState] = useState<FreshLoginState>({
    isModalOpen: false,
    isLoading: false,
    error: null,
    pendingOperations: [],
  });

  const showFreshLoginModal = useCallback(
    (retryOperation: () => Promise<void>) => {
      setState((prevState) => ({
        ...prevState,
        isModalOpen: true,
        error: null,
        pendingOperations: [...prevState.pendingOperations, retryOperation],
      }));
    },
    [],
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

        // On success, retrieve and execute all pending operations
        // Use functional setState to get current state instead of stale closure
        let operationsToRetry: (() => Promise<void>)[] = [];

        setState((prevState) => {
          operationsToRetry = prevState.pendingOperations;
          return {
            ...prevState,
            isLoading: false,
            error: null,
            // Keep modal open and don't clear pending operations yet
          };
        });

        // Explicitly fetch new CSRF token after password verification
        // The backend generates a new CSRF token and updates the session during password verification
        // Fetching it explicitly ensures we have the correct token that matches the server session
        await getCsrfToken();

        // Execute all pending operations - keep modal open until all complete
        for (const operation of operationsToRetry) {
          await operation(); // Let errors propagate to the original error handler
        }

        // All operations succeeded - now close the modal and clear pending operations
        setState({
          isModalOpen: false,
          isLoading: false,
          error: null,
          pendingOperations: [],
        });
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
    [], // Remove state.pendingOperations from dependencies - we read from prevState instead
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
