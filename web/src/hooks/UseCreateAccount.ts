import {useState} from 'react';
import {useNavigate} from 'react-router-dom';
import {AxiosError} from 'axios';
import {createUser} from 'src/resources/UserResource';
import {
  loginUser,
  GlobalAuthState,
  getCsrfToken,
} from 'src/resources/AuthResource';
import {addDisplayError} from 'src/resources/ErrorHandling';

export function useCreateAccount() {
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const navigate = useNavigate();

  const createAccountWithAutoLogin = async (
    username: string,
    password: string,
    email: string,
  ) => {
    setIsLoading(true);
    setError(null);

    try {
      // Create the user account
      await createUser(username, password, email);

      // Clear CSRF token after account creation (session state changed)
      GlobalAuthState.csrfToken = null;

      // Auto-login after successful account creation
      try {
        const loginResponse = await loginUser(username, password);

        if (loginResponse.success === true) {
          // Login successful, set auth state and redirect
          await getCsrfToken();
          GlobalAuthState.isLoggedIn = true;
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
