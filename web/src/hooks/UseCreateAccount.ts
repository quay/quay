import {useState} from 'react';
import {useNavigate} from 'react-router-dom';
import {AxiosError} from 'axios';
import {createUser, fetchUser} from 'src/resources/UserResource';
import {
  loginUser,
  GlobalAuthState,
  getCsrfToken,
} from 'src/resources/AuthResource';
import {addDisplayError} from 'src/resources/ErrorHandling';
import {useQueryClient} from '@tanstack/react-query';

export function useCreateAccount() {
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const createAccountWithAutoLogin = async (
    username: string,
    password: string,
    email: string,
  ) => {
    setIsLoading(true);
    setError(null);

    try {
      // Create the user account
      const response = await createUser(username, password, email);

      // Clear CSRF token after account creation (session state changed)
      GlobalAuthState.csrfToken = null;

      // Check if email verification is required
      if (response.awaiting_verification === true) {
        // Email verification required, return success but indicate verification is needed
        return {success: true, awaitingVerification: true};
      }

      // Auto-login after successful account creation
      try {
        const loginResponse = await loginUser(username, password);

        if (loginResponse.success === true) {
          // Login successful, set auth state
          await getCsrfToken();
          GlobalAuthState.isLoggedIn = true;

          // Fetch fresh user data to check for prompts
          let user;
          try {
            user = await queryClient.fetchQuery(['user'], fetchUser);
          } catch (fetchErr) {
            // If fetching user fails, show error
            setError(
              addDisplayError(
                'Account created but failed to load user data. Please sign in.',
                fetchErr,
              ),
            );
            return {success: false};
          }

          // If user has prompts (e.g., confirm_username, enter_name, enter_company), redirect to updateuser
          if (user.prompts && user.prompts.length > 0) {
            navigate('/updateuser');
            return {success: true};
          }

          // Otherwise, redirect to organizations page
          navigate('/organization');
          return {success: true};
        }
      } catch (loginErr) {
        // Auto-login failed, redirect to signin with message
        navigate('/signin?account_created=true&auto_login_failed=true');
        return {success: true, autoLoginFailed: true};
      }
    } catch (err) {
      const authErr = err instanceof AxiosError && err.response;
      if (authErr && err.response.status === 409) {
        setError('Username or email already exists');
      } else {
        setError(addDisplayError('Unable to create account', err));
      }
      return {success: false};
    } finally {
      setIsLoading(false);
    }
  };

  return {
    createAccountWithAutoLogin,
    isLoading,
    error,
    setError,
  };
}
