import {AxiosResponse, InternalAxiosRequestConfig} from 'axios';
import axios from 'src/libs/axios';
import {
  loginUser,
  logoutUser,
  getCsrfToken,
  getUser,
  getOrganization,
  getExternalLoginAuthUrl,
  detachExternalLogin,
  verifyUser,
  GlobalAuthState,
} from './AuthResource';

vi.mock('src/libs/axios', () => ({
  default: {
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
    delete: vi.fn(),
  },
}));

/** Creates a mock Axios response with the given data and status. */
function mockResponse(data: unknown, status = 200): AxiosResponse {
  return {
    data,
    status,
    statusText: 'OK',
    headers: {},
    config: {} as InternalAxiosRequestConfig,
  };
}

describe('AuthResource', () => {
  beforeEach(() => {
    localStorage.clear();
    GlobalAuthState.isLoggedIn = false;
    GlobalAuthState.csrfToken = null;
    GlobalAuthState.bearerToken = null;
  });

  describe('loginUser', () => {
    it('sets GlobalAuthState on successful login', async () => {
      vi.mocked(axios.post).mockResolvedValueOnce(
        mockResponse({success: true}),
      );

      const result = await loginUser('alice', 'password');
      expect(axios.post).toHaveBeenCalledWith('/api/v1/signin', {
        username: 'alice',
        password: 'password',
      });
      expect(result.success).toBe(true);
      expect(GlobalAuthState.isLoggedIn).toBe(true);
    });

    it('does not set isLoggedIn on failed login', async () => {
      vi.mocked(axios.post).mockResolvedValueOnce(
        mockResponse({success: false}),
      );

      await loginUser('alice', 'wrong');
      expect(GlobalAuthState.isLoggedIn).toBe(false);
    });
  });

  describe('logoutUser', () => {
    it('clears GlobalAuthState on logout', async () => {
      GlobalAuthState.isLoggedIn = true;
      vi.mocked(axios.post).mockResolvedValueOnce(mockResponse({}));

      await logoutUser();
      expect(axios.post).toHaveBeenCalledWith('/api/v1/signout');
      expect(GlobalAuthState.isLoggedIn).toBe(false);
    });
  });

  describe('getCsrfToken', () => {
    it('stores CSRF token in GlobalAuthState', async () => {
      vi.mocked(axios.get).mockResolvedValueOnce(
        mockResponse({csrf_token: 'tok123'}),
      );

      const result = await getCsrfToken();
      expect(axios.get).toHaveBeenCalledWith('/csrf_token');
      expect(GlobalAuthState.csrfToken).toBe('tok123');
      expect(result.csrf_token).toBe('tok123');
    });
  });

  describe('getUser', () => {
    it('fetches user by username', async () => {
      const resp = mockResponse({username: 'alice'});
      vi.mocked(axios.get).mockResolvedValueOnce(resp);

      const result = await getUser('alice');
      expect(axios.get).toHaveBeenCalledWith('api/v1/users/alice');
      expect(result).toBe(resp);
    });
  });

  describe('getOrganization', () => {
    it('fetches organization by name', async () => {
      const resp = mockResponse({name: 'myorg'});
      vi.mocked(axios.get).mockResolvedValueOnce(resp);

      const result = await getOrganization('myorg');
      expect(axios.get).toHaveBeenCalledWith('api/v1/organization/myorg');
      expect(result).toBe(resp);
    });
  });

  describe('getExternalLoginAuthUrl', () => {
    it('returns auth URL for a service', async () => {
      vi.mocked(axios.post).mockResolvedValueOnce(
        mockResponse({auth_url: 'https://auth.example.com'}),
      );

      const result = await getExternalLoginAuthUrl('github');
      expect(axios.post).toHaveBeenCalledWith('/api/v1/externallogin/github', {
        kind: 'login',
      });
      expect(result.auth_url).toBe('https://auth.example.com');
    });

    it('passes custom action', async () => {
      vi.mocked(axios.post).mockResolvedValueOnce(mockResponse({}));

      await getExternalLoginAuthUrl('google', 'attach');
      expect(axios.post).toHaveBeenCalledWith('/api/v1/externallogin/google', {
        kind: 'attach',
      });
    });
  });

  describe('detachExternalLogin', () => {
    it('detaches external login provider', async () => {
      vi.mocked(axios.post).mockResolvedValueOnce(mockResponse({}));

      await detachExternalLogin('github');
      expect(axios.post).toHaveBeenCalledWith('/api/v1/detachexternal/github');
    });
  });

  describe('verifyUser', () => {
    it('verifies user password', async () => {
      vi.mocked(axios.post).mockResolvedValueOnce(
        mockResponse({success: true}),
      );

      const result = await verifyUser('mypassword');
      expect(axios.post).toHaveBeenCalledWith('/api/v1/signin/verify', {
        password: 'mypassword',
      });
      expect(result.success).toBe(true);
    });
  });
});
