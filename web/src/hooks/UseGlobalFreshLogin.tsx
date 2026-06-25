import {useState, useCallback} from 'react';
import {AxiosError} from 'axios';
import {
  getCsrfToken,
  retryPendingFreshLoginRequests,
  clearPendingFreshLoginRequests,
} from 'src/libs/axios';
import {verifyUser} from 'src/resources/AuthResource';

export function useGlobalFreshLogin() {
  const [isLoading, setIsLoading] = useState(false);

  const handleVerify = useCallback(async (password: string) => {
    setIsLoading(true);

    try {
      // Verify password with backend
      await verifyUser(password);

      // Fetch new CSRF token after password verification
      await getCsrfToken();

      // Retry all queued requests that failed due to fresh login requirement
      retryPendingFreshLoginRequests();

      // Reset state
      setIsLoading(false);
    } catch (err: unknown) {
      const axiosError = err as AxiosError;
      const errorMessage =
        ((axiosError?.response?.data as Record<string, unknown>)
          ?.message as string) || 'Invalid verification credentials';
      setIsLoading(false);

      // Reject all queued requests with error
      clearPendingFreshLoginRequests(errorMessage);

      // Throw error to allow parent component to handle verification failure
      throw new Error(errorMessage);
    }
  }, []);

  const handleCancel = useCallback(() => {
    // Reject all queued requests
    clearPendingFreshLoginRequests('Verification canceled');
    setIsLoading(false);
  }, []);

  return {
    isLoading,
    handleVerify,
    handleCancel,
  };
}
