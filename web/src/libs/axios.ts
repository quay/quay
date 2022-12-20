// axios
import axios from 'axios';
import {GlobalAuthState} from 'src/resources/AuthResource';

if (process.env.MOCK_API === 'true') {
  require('src/tests/fake-db/ApiMock');
}

axios.defaults.baseURL =
  process.env.REACT_QUAY_APP_API_URL ||
  `${window.location.protocol}//${window.location.host}`;
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

const axiosIns = axios.create();
axiosIns.interceptors.request.use(async (config) => {
  if (!GlobalAuthState.csrfToken) {
    const r = await getCsrfToken();
    GlobalAuthState.csrfToken = r.csrf_token;
  }

  if (config.headers && GlobalAuthState.csrfToken) {
    config.headers['X-CSRF-Token'] = GlobalAuthState.csrfToken;
  }

  return config;
});

// Catches errors thrown in axiosIns.interceptors.request.use
axiosIns.interceptors.response.use(
  (response) => {
    return response;
  },
  (error) => {
    if (error.response?.status === 401) {
      window.location.href = '/signin';
    }
    throw error; // Rethrow error to be handled in components
  },
);

export default axiosIns;
