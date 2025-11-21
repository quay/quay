import {useParams, useSearchParams} from 'react-router-dom';
import {OAuthError} from './OAuthError';

interface OAuthCallbackParams {
  provider: string;
}

export function OAuthCallbackHandler() {
  const {provider} = useParams<OAuthCallbackParams>();
  const [searchParams] = useSearchParams();

  const error = searchParams.get('error');

  if (error) {
    // Only handle errors in React to show consistent UI
    return <OAuthError provider={provider!} searchParams={searchParams} />;
  }

  // For success (code param) - redirect to backend immediately
  const baseURL =
    process.env.REACT_QUAY_APP_API_URL ||
    `${window.location.protocol}//${window.location.host}`;
  window.location.href = `${baseURL}/oauth2/${provider}/callback?${searchParams.toString()}`;
  return null;
}
