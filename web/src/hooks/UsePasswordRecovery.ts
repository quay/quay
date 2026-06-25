import {useState} from 'react';
import axios from 'src/libs/axios';
import {AxiosError} from 'axios';

export interface RecoveryResponse {
  status: 'sent' | 'org';
  orgemail?: string;
  orgname?: string;
}

export interface RecoveryRequest {
  email: string;
}

export function usePasswordRecovery() {
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<RecoveryResponse | null>(null);

  const requestRecovery = async (email: string) => {
    setIsLoading(true);
    setError(null);
    setResult(null);

    try {
      const payload: RecoveryRequest = {email};

      const response = await axios.post('/api/v1/recovery', payload);
      setResult(response.data);
      return response.data;
    } catch (err) {
      const errorMessage =
        err instanceof AxiosError && err.response?.data?.message
          ? err.response.data.message
          : 'Cannot send recovery email';
      setError(errorMessage);
      throw err;
    } finally {
      setIsLoading(false);
    }
  };

  const resetState = () => {
    setError(null);
    setResult(null);
    setIsLoading(false);
  };

  return {
    requestRecovery,
    isLoading,
    error,
    result,
    setError,
    resetState,
  };
}
