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
  const [error, setError] = useState<string | null>(null);

  const handleVerify = useCallback(async (password: string) => {
    setIsLoading(true);
    setError(null);

    try {
      // Verify password with backend
      await verifyUser(password);

      // Fetch new CSRF token after password verification
      await getCsrfToken();

      // Retry all queued requests that failed due to fresh login requirement
      retryPendingFreshLoginRequests();

      // Reset state
      setIsLoading(false);
      setError(null);
    } catch (err: unknown) {
      const axiosError = err as AxiosError;
      const errorMessage =
        ((axiosError?.response?.data as Record<string, unknown>)
          ?.message as string) || 'Invalid verification credentials';
      setIsLoading(false);
      setError(errorMessage);
    }
  }, []);

  const handleCancel = useCallback(() => {
    // Reject all queued requests
    clearPendingFreshLoginRequests();
    setIsLoading(false);
    setError(null);
  }, []);

  return {
    isLoading,
    error,
    handleVerify,
    handleCancel,
  };
}
