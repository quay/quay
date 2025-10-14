import {useState, useCallback} from 'react';
import {useMutation} from '@tanstack/react-query';
import axios from 'src/libs/axios';

type ValidationState =
  | 'editing'
  | 'confirming'
  | 'confirmed'
  | 'existing'
  | 'error';

export function useUsernameValidation(currentUsername?: string) {
  const [state, setState] = useState<ValidationState>('editing');

  const checkUsernameMutation = useMutation(
    async (username: string) => {
      if (username === currentUsername) {
        setState('confirmed');
        return;
      }

      // Check if user exists
      try {
        await axios.get(`/api/v1/users/${username}`);
        setState('existing');
        return;
      } catch (userError) {
        // User doesn't exist, check organization
        try {
          await axios.get(`/api/v1/organization/${username}`);
          setState('existing');
          return;
        } catch (orgError) {
          setState('confirmed');
        }
      }
    },
    {
      onMutate: () => setState('confirming'),
      onError: () => setState('error'),
    },
  );

  const validateUsername = useCallback(
    (username: string) => {
      if (!username) {
        setState('editing');
        return;
      }
      checkUsernameMutation.mutate(username);
    },
    [checkUsernameMutation],
  );

  return {
    state,
    validateUsername,
    isValidating: checkUsernameMutation.isLoading,
  };
}
