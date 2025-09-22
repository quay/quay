import React from 'react';
import {Button, Spinner} from '@patternfly/react-core';
import {ExternalLoginProvider} from 'src/hooks/UseExternalLogins';
import {useExternalLoginAuth} from 'src/hooks/UseExternalLoginAuth';

interface ExternalLoginButtonProps {
  provider: ExternalLoginProvider;
  redirectUrl?: string;
  isLink?: boolean;
  action?: 'login' | 'attach';
  onSignInStarted?: (provider: ExternalLoginProvider) => void;
  disabled?: boolean;
}

export function ExternalLoginButton({
  provider,
  redirectUrl,
  isLink = false,
  action = 'login',
  onSignInStarted,
  disabled = false,
}: ExternalLoginButtonProps) {
  const {isAuthenticating, startExternalLogin} = useExternalLoginAuth();

  const handleClick = async () => {
    if (onSignInStarted) {
      onSignInStarted(provider);
    }
    await startExternalLogin(provider, redirectUrl);
  };

  const buttonText =
    action === 'attach'
      ? `Attach to ${provider.title}`
      : `Sign in with ${provider.title}`;

  if (isLink) {
    return (
      <button
        type="button"
        className="signin-link-button"
        onClick={handleClick}
        disabled={disabled || isAuthenticating}
        data-testid={`${action}-${provider.id}`}
      >
        {isAuthenticating ? <Spinner size="sm" /> : null}
        {buttonText}
      </button>
    );
  }

  return (
    <Button
      variant="secondary"
      isBlock
      onClick={handleClick}
      isDisabled={disabled || isAuthenticating}
      className="external-login-button"
      data-testid={`external-login-${provider.id}`}
    >
      {isAuthenticating ? (
        <Spinner size="sm" className="external-login-spinner" />
      ) : (
        <span className="external-login-icon" data-icon={provider.icon}></span>
      )}
      <span className="external-login-text">
        {action !== 'attach' && (
          <span className="prefix">Sign in with&nbsp;</span>
        )}
        <span className="suffix">{provider.title}</span>
      </span>
    </Button>
  );
}
