import React, {useState, useEffect} from 'react';
import {
  Alert,
  Button,
  Card,
  CardBody,
  CardTitle,
  PageSection,
  Spinner,
} from '@patternfly/react-core';
import {useNavigate} from 'react-router-dom';
import axios from 'src/libs/axios';
import {AxiosError} from 'axios';

interface OAuthErrorProps {
  provider: string;
  searchParams: URLSearchParams;
}

const FALLBACK_ERROR_MESSAGES = {
  ologinerror: (provider: string) =>
    `The e-mail address is already associated with an existing account. Please log in with your username and password and associate your ${provider} account.`,
  access_denied: 'Access was denied. Please try again.',
  invalid_request: 'Invalid OAuth request. Please try again.',
  invalid_provider: 'Invalid OAuth provider specified.',
};

export function OAuthError({provider, searchParams}: OAuthErrorProps) {
  const navigate = useNavigate();
  const [backendError, setBackendError] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  const error = searchParams.get('error');
  const errorDescription = searchParams.get('error_description');

  useEffect(() => {
    const fetchErrorDetails = async () => {
      try {
        setLoading(true);
        const params = new URLSearchParams(searchParams);
        const baseURL =
          process.env.REACT_QUAY_APP_API_URL ||
          `${window.location.protocol}//${window.location.host}`;
        await axios.get(
          `${baseURL}/oauth2/${provider}/callback?${params.toString()}`,
          {
            headers: {Accept: 'application/json'},
          },
        );
      } catch (err) {
        if (err instanceof AxiosError && err.response?.data?.error_info) {
          setBackendError(err.response.data.error_info);
        }
      } finally {
        setLoading(false);
      }
    };

    fetchErrorDetails();
  }, [provider, searchParams]);

  let errorMessage = 'An unknown error occurred during authentication.';

  if (backendError?.error_message) {
    errorMessage = backendError.error_message;
  } else if (errorDescription) {
    errorMessage = errorDescription;
  } else if (error && error in FALLBACK_ERROR_MESSAGES) {
    const messageFunc =
      FALLBACK_ERROR_MESSAGES[error as keyof typeof FALLBACK_ERROR_MESSAGES];
    errorMessage =
      typeof messageFunc === 'function' ? messageFunc(provider) : messageFunc;
  }

  const handleSignIn = () => {
    navigate('/signin');
  };

  const handleRetryOAuth = () => {
    navigate('/signin');
  };

  if (loading) {
    return (
      <PageSection>
        <div style={{textAlign: 'center', padding: '2rem'}}>
          <Spinner size="lg" />
          <p>Loading error details...</p>
        </div>
      </PageSection>
    );
  }

  return (
    <PageSection>
      <Card style={{maxWidth: '500px', margin: '0 auto'}}>
        <CardTitle>{provider} Authentication Error</CardTitle>
        <CardBody>
          <Alert variant="danger" title="Authentication Failed" isInline>
            {errorMessage}
          </Alert>

          {backendError?.register_redirect && (
            <Alert
              variant="info"
              title="Account Association"
              isInline
              style={{marginTop: '1rem'}}
            >
              You can associate your {provider} account after signing in with
              your username and password.
            </Alert>
          )}

          <div style={{marginTop: '1rem', display: 'flex', gap: '1rem'}}>
            <Button variant="primary" onClick={handleSignIn}>
              Sign in with username/password
            </Button>
            <Button variant="secondary" onClick={handleRetryOAuth}>
              Try again
            </Button>
          </div>
        </CardBody>
      </Card>
    </PageSection>
  );
}
