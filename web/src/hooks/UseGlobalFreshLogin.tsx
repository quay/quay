import {useState, useCallback} from 'react';
import {AxiosError} from 'axios';
import {getCsrfToken} from 'src/libs/axios';
import {verifyUser} from 'src/resources/AuthResource';
import {useQueryClient} from '@tanstack/react-query';

export function useGlobalFreshLogin() {
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const queryClient = useQueryClient();

  const isFreshLoginRequired = useCallback((error: unknown): boolean => {
    const axiosError = error as AxiosError;
    if (axiosError?.response?.status !== 401) return false;

    const data = axiosError.response?.data as Record<string, unknown>;
    return (
      data?.title === 'fresh_login_required' ||
      data?.error_type === 'fresh_login_required'
    );
  }, []);

  const handleError = useCallback(
    (error: unknown) => {
      if (isFreshLoginRequired(error)) {
        setIsModalOpen(true);
        setError(null);
      }
    },
    [isFreshLoginRequired],
  );

  const handleVerify = useCallback(
    async (password: string) => {
      setIsLoading(true);
      setError(null);

      try {
        await verifyUser(password);

        // Explicitly fetch new CSRF token after password verification
        await getCsrfToken();

        // Invalidate all queries to trigger refetch
        await queryClient.invalidateQueries();

        setIsModalOpen(false);
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
    },
    [queryClient],
  );

  const handleCancel = useCallback(() => {
    setIsModalOpen(false);
    setIsLoading(false);
    setError(null);
  }, []);

  return {
    isModalOpen,
    isLoading,
    error,
    handleError,
    handleVerify,
    handleCancel,
    isFreshLoginRequired,
  };
}
