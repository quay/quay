import {useParams, useSearchParams} from 'react-router-dom';

interface OAuthCallbackParams {
  provider: string;
}

export function OAuthCallbackHandler() {
  const {provider} = useParams<OAuthCallbackParams>();
  const [searchParams] = useSearchParams();

  const error = searchParams.get('error');

  // Note: For React, backend redirects to /oauth-error when error occurs.
  if (error) {
    // Redirect to centralized error page
    const errorParams = new URLSearchParams({
      error: error,
      error_description: searchParams.get('error_description') || error,
      provider: provider || 'OAuth Provider',
    });
    window.location.href = `/oauth-error?${errorParams.toString()}`;
    return null;
  }

  // For success (code param) - redirect to backend immediately
  const baseURL =
    process.env.REACT_QUAY_APP_API_URL ||
    `${window.location.protocol}//${window.location.host}`;
  // Preserve the full path including /attach or /cli suffix
  const fullPath = window.location.pathname;
  window.location.href = `${baseURL}${fullPath}?${searchParams.toString()}`;
  return null;
}
