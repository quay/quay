import {
  Alert,
  Button,
  Card,
  CardBody,
  CardTitle,
  EmptyState,
  EmptyStateHeader,
  EmptyStateIcon,
  Page,
  PageSection,
} from '@patternfly/react-core';
import {ExclamationCircleIcon} from '@patternfly/react-icons';
import {useNavigate, useSearchParams} from 'react-router-dom';
import {MinimalHeader} from 'src/components/header/MinimalHeader';
import './OAuthError.css';

export function OAuthError() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();

  const errorDescription = searchParams.get('error_description');
  const provider = searchParams.get('provider') || 'OAuth Provider';
  const registerRedirect = searchParams.get('register_redirect') === 'true';
  const userCreation = searchParams.get('user_creation') === 'true';

  const displayMessage =
    errorDescription || 'An unknown error occurred during authentication.';

  const handleSignIn = () => {
    navigate('/signin');
  };

  return (
    <Page header={<MinimalHeader />}>
      <PageSection isFilled>
        <div className="oauth-error-container">
          <Card className="oauth-error-card">
            <CardTitle>
              <EmptyState>
                <EmptyStateHeader
                  titleText={`${provider} Authentication Error`}
                  icon={
                    <EmptyStateIcon
                      icon={ExclamationCircleIcon}
                      color="var(--pf-v5-global--danger-color--100)"
                    />
                  }
                  headingLevel="h2"
                />
              </EmptyState>
            </CardTitle>
            <CardBody>
              <Alert
                variant="danger"
                title="Authentication Failed"
                isInline
                className="oauth-error-alert"
              >
                {displayMessage}
              </Alert>

              {registerRedirect && userCreation && (
                <Alert
                  variant="info"
                  title="Account Registration Required"
                  isInline
                  className="oauth-error-alert"
                >
                  To continue, please register using the sign-in form. You will
                  be able to reassociate this {provider} account to your new
                  account in the user settings panel.
                </Alert>
              )}

              <div className="oauth-error-actions">
                <Button variant="primary" onClick={handleSignIn}>
                  Return to Sign In
                </Button>
              </div>
            </CardBody>
          </Card>
        </div>
      </PageSection>
    </Page>
  );
}
