import React, {useEffect, useState} from 'react';
import {Alert, Button, Spinner} from '@patternfly/react-core';
import {useNavigate, useSearchParams} from 'react-router-dom';
import {useMutation} from '@tanstack/react-query';
import {acceptTeamInvite} from 'src/resources/TeamResources';
import {useCurrentUser} from 'src/hooks/UseCurrentUser';
import {useQuayConfigWithLoading} from 'src/hooks/UseQuayConfig';
import {LoginPageLayout} from 'src/components/LoginPageLayout';

export function ConfirmInvite(): React.ReactElement {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const code = searchParams.get('code') || '';
  const [errorMessage, setErrorMessage] = useState<string>('');

  const {isLoading: configLoading} = useQuayConfigWithLoading();
  const {user, loading: userLoading, error: userError} = useCurrentUser(!!code);

  const {mutate: doAcceptInvite, isLoading: isAccepting} = useMutation(
    () => acceptTeamInvite(code),
    {
      onSuccess: (resp) => {
        navigate(`/organization/${resp.org}/teams/${resp.team}`);
      },
      onError: (err: any) => {
        setErrorMessage(
          err?.response?.data?.message || 'Invalid or expired invite code.',
        );
      },
    },
  );

  useEffect(() => {
    if (!code || userLoading || user === undefined) return;
    if (!user.anonymous) {
      doAcceptInvite();
    }
  }, [code, user, userLoading, doAcceptInvite]);

  if (!code) {
    return (
      <LoginPageLayout
        title="Confirm Invitation"
        description="Accept your team invitation to collaborate on Quay."
      >
        <Alert
          variant="danger"
          isInline
          title="Unable to process invitation"
          data-testid="confirm-invite-error"
        >
          No invite code found in the URL.
        </Alert>
      </LoginPageLayout>
    );
  }

  if (configLoading || userLoading) {
    return (
      <LoginPageLayout
        title="Confirm Invitation"
        description="Accept your team invitation to collaborate on Quay."
      >
        <div style={{textAlign: 'center', padding: '40px'}}>
          <Spinner size="xl" data-testid="confirm-invite-loading" />
        </div>
      </LoginPageLayout>
    );
  }

  const signinUrl = `/signin?code=${encodeURIComponent(code)}`;
  const createAccountUrl = `/createaccount?code=${encodeURIComponent(code)}`;
  const showUnauthenticated =
    !isAccepting && !errorMessage && (userError || user?.anonymous);

  return (
    <LoginPageLayout
      title="Confirm Invitation"
      description="Accept your team invitation to collaborate on Quay."
    >
      {isAccepting && (
        <div style={{textAlign: 'center', padding: '40px'}}>
          <Spinner
            size="xl"
            data-testid={
              isAccepting
                ? 'confirm-invite-accepting'
                : 'confirm-invite-loading'
            }
          />
          {isAccepting && (
            <p style={{marginTop: '16px'}}>Accepting invitation…</p>
          )}
        </div>
      )}

      {showUnauthenticated && (
        <div data-testid="confirm-invite-unauthenticated">
          <Alert
            variant="info"
            isInline
            title="Sign in or create an account to accept this invitation"
            style={{marginBottom: '24px'}}
          >
            You have been invited to join a team. Please sign in or create a new
            account to accept this invitation.
          </Alert>
          <div style={{display: 'flex', gap: '12px', flexDirection: 'column'}}>
            <Button
              variant="primary"
              isBlock
              component="a"
              href={signinUrl}
              data-testid="confirm-invite-signin-btn"
            >
              Sign in
            </Button>
            <Button
              variant="secondary"
              isBlock
              component="a"
              href={createAccountUrl}
              data-testid="confirm-invite-create-account-btn"
            >
              Create account
            </Button>
          </div>
        </div>
      )}

      {errorMessage && (
        <Alert
          variant="danger"
          isInline
          title="Unable to process invitation"
          data-testid="confirm-invite-error"
        >
          {errorMessage}
        </Alert>
      )}
    </LoginPageLayout>
  );
}
