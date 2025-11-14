// axios
import axios from 'axios';
import {GlobalAuthState} from 'src/resources/AuthResource';

if (process.env.MOCK_API === 'true') {
  require('src/tests/fake-db/ApiMock');
}

axios.defaults.withCredentials = true;
axios.defaults.headers.common['X-Requested-With'] = 'XMLHttpRequest';

export async function getCsrfToken() {
  if (process.env.MOCK_API === 'true') {
    return 'test-csrf-token';
  }
  const response = await axios.get('/csrf_token');
  GlobalAuthState.csrfToken = response.data.csrf_token;
  return response.data;
}

// Queue for requests that failed due to fresh login requirement
let pendingFreshLoginRequests: Array<{
  config: any;
  resolve: (value: any) => void;
  reject: (reason: any) => void;
}> = [];

// Tracks whether fresh login modal is currently displayed
let freshLoginModalShown = false;

const axiosIns = axios.create();
axiosIns.interceptors.request.use(async (config) => {
  if (!GlobalAuthState.csrfToken) {
    const r = await getCsrfToken();
    GlobalAuthState.csrfToken = r.csrf_token;
  }

  if (!GlobalAuthState.bearerToken && window?.insights?.chrome?.auth) {
    GlobalAuthState.bearerToken = await window.insights.chrome.auth.getToken();
  }

  if (config.headers && GlobalAuthState.csrfToken) {
    config.headers['X-CSRF-Token'] = GlobalAuthState.csrfToken;
  }

  if (config.headers && GlobalAuthState.bearerToken) {
    config.headers['Authorization'] = `Bearer ${GlobalAuthState.bearerToken}`;
  }

  return config;
});

axiosIns.interceptors.response.use(
  (response) => {
    // Update CSRF token from response headers when backend provides a new one
    const nextCsrfToken = response.headers['x-next-csrf-token'];
    if (nextCsrfToken) {
      GlobalAuthState.csrfToken = nextCsrfToken;
    }
    return response;
  },
  async (error) => {
    if (error.response?.status === 401) {
      const data = error.response?.data;
      const isFreshLoginRequired =
        data?.title === 'fresh_login_required' ||
        data?.error_type === 'fresh_login_required';

      if (isFreshLoginRequired) {
        // Queue this request to be retried after password verification
        return new Promise((resolve, reject) => {
          pendingFreshLoginRequests.push({
            config: error.config,
            resolve,
            reject,
          });

          // Only show modal for the first failed request to avoid duplicates
          if (!freshLoginModalShown) {
            freshLoginModalShown = true;
            window.dispatchEvent(new CustomEvent('freshLoginRequired'));
          }
        });
      }

      // Handle regular session expiry
      if (!isFreshLoginRequired) {
        if (window?.insights?.chrome?.auth) {
          // Refresh token for plugin
          GlobalAuthState.bearerToken =
            await window.insights.chrome.auth.getToken();
        } else {
          // Redirect to login page for standalone
          window.location.href = '/signin';
        }
      }
    }
    throw error;
  },
);

// Retry all queued requests after successful password verification
export function retryPendingFreshLoginRequests() {
  const requests = [...pendingFreshLoginRequests];
  pendingFreshLoginRequests = [];
  freshLoginModalShown = false;

  for (const {config, resolve, reject} of requests) {
    axiosIns.request(config).then(resolve).catch(reject);
  }
}

// Clear all pending requests when user cancels password verification
export function clearPendingFreshLoginRequests() {
  pendingFreshLoginRequests.forEach(({reject}) =>
    reject(new Error('Fresh login verification cancelled')),
  );
  pendingFreshLoginRequests = [];
  freshLoginModalShown = false;
}

export default axiosIns;
