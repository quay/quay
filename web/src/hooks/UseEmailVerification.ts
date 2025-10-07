import {useState} from 'react';
import axios from 'src/libs/axios';
import {addDisplayError} from 'src/resources/ErrorHandling';

interface VerificationData {
  code: string;
  username?: string;
}

export function useEmailVerification() {
  const [isVerifying, setIsVerifying] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  const verifyUser = async (data: VerificationData) => {
    setIsVerifying(true);
    setError(null);
    setSuccess(false);

    try {
      const response = await axios.post('/api/v1/signin/verify', data);
      setSuccess(true);
      return response.data;
    } catch (err) {
      const errorMsg = addDisplayError('Email verification failed', err);
      setError(errorMsg);
      throw new Error(errorMsg);
    } finally {
      setIsVerifying(false);
    }
  };

  const resetVerification = () => {
    setError(null);
    setSuccess(false);
    setIsVerifying(false);
  };

  return {
    verifyUser,
    isVerifying,
    error,
    success,
    resetVerification,
  };
}
