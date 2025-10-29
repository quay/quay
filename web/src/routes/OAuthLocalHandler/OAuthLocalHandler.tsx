import React, {useEffect, useState} from 'react';
import {useSearchParams, useNavigate} from 'react-router-dom';
import {
  Alert,
  AlertVariant,
  PageSection,
  PageSectionVariants,
  Spinner,
} from '@patternfly/react-core';
import TokenDisplayModal from 'src/components/modals/TokenDisplayModal';

interface OAuthTokenData {
  access_token: string;
  scope: string;
  state?: string;
}

export default function OAuthLocalHandler() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const [tokenData, setTokenData] = useState<OAuthTokenData | null>(null);
  const [isTokenModalOpen, setIsTokenModalOpen] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    // Extract token from URL hash
    const hash = window.location.hash.substring(1);
    if (!hash) {
      setError('Authorization was cancelled');
      setIsLoading(false);
      return;
    }

    const params = new URLSearchParams(hash);
    const token = params.get('access_token');
    const scope = params.get('scope');
    const state = params.get('state');

    if (!token) {
      setError('No access token received');
      setIsLoading(false);
      return;
    }

    // Store token data
    const data: OAuthTokenData = {
      access_token: token,
      scope: scope || '',
      state: state || undefined,
    };
    setTokenData(data);

    // Check if format=json requested (for API clients)
    if (searchParams.get('format') === 'json') {
      document.body.innerHTML = JSON.stringify({access_token: token});
      setIsLoading(false);
      return;
    }

    // Check if opened in popup window
    if (window.opener && !window.opener.closed) {
      try {
        // Send token to parent window
        window.opener.postMessage(
          {
            type: 'OAUTH_TOKEN_GENERATED',
            token: token,
            scope: scope,
            state: state,
          },
          window.location.origin,
        );

        // Close popup after message sent
        setTimeout(() => {
          window.close();
        }, 500);
      } catch (err) {
        console.error('Failed to communicate with parent window:', err);
        // If postMessage fails, show modal in popup
        setIsTokenModalOpen(true);
      }
    } else {
      // Opened in same tab - show modal
      setIsTokenModalOpen(true);
    }

    setIsLoading(false);
  }, [searchParams]);

  const handleModalClose = () => {
    setIsTokenModalOpen(false);
    // Navigate back to home or organization page
    navigate('/organization');
  };

  if (isLoading) {
    return (
      <PageSection variant={PageSectionVariants.light}>
        <Spinner />
      </PageSection>
    );
  }

  if (error) {
    return (
      <PageSection variant={PageSectionVariants.light}>
        <Alert variant={AlertVariant.warning} title="Authorization Cancelled">
          {error}
        </Alert>
      </PageSection>
    );
  }

  if (!tokenData) {
    return null;
  }

  const scopes = tokenData.scope ? tokenData.scope.split(' ') : [];

  return (
    <>
      {isTokenModalOpen && (
        <TokenDisplayModal
          isOpen={isTokenModalOpen}
          onClose={handleModalClose}
          token={tokenData.access_token}
          applicationName="OAuth Application"
          scopes={scopes}
        />
      )}
    </>
  );
}
