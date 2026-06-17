import {render, screen, waitFor, act} from 'src/test-utils';
import {MemoryRouter, Route, Routes} from 'react-router-dom';
import UpdateUser from './UpdateUser';

let capturedOnSuccess: (user: any) => void;

vi.mock('src/hooks/UseCurrentUser', () => ({
  useCurrentUser: vi.fn(),
  useUpdateUser: ({onSuccess}: {onSuccess: (user: any) => void}) => {
    capturedOnSuccess = onSuccess;
    return {updateUser: vi.fn()};
  },
}));

vi.mock('src/hooks/UseUsernameValidation', () => ({
  useUsernameValidation: () => ({
    state: 'editing',
    validateUsername: vi.fn(),
  }),
}));

import {useCurrentUser} from 'src/hooks/UseCurrentUser';

function renderUpdateUser(search = '') {
  return render(
    <MemoryRouter initialEntries={[`/updateuser${search}`]}>
      <Routes>
        <Route path="/updateuser" element={<UpdateUser />} />
        <Route
          path="/confirminvite"
          element={<div data-testid="confirminvite-page">ConfirmInvite</div>}
        />
        <Route
          path="/signin"
          element={<div data-testid="signin-page">Signin</div>}
        />
        <Route path="/" element={<div data-testid="home-page">Home</div>} />
      </Routes>
    </MemoryRouter>,
  );
}

describe('UpdateUser', () => {
  beforeEach(() => {
    sessionStorage.clear();
    vi.clearAllMocks();
  });

  it('redirects to / when user has no prompts and no invite code', async () => {
    vi.mocked(useCurrentUser).mockReturnValue({
      user: {anonymous: false, prompts: [], username: 'testuser'},
      loading: false,
      error: null,
    } as any);

    renderUpdateUser();

    await waitFor(() => {
      expect(screen.getByTestId('home-page')).toBeInTheDocument();
    });
  });

  it('redirects to confirminvite when user has no prompts and code query param', async () => {
    vi.mocked(useCurrentUser).mockReturnValue({
      user: {anonymous: false, prompts: [], username: 'testuser'},
      loading: false,
      error: null,
    } as any);

    renderUpdateUser('?code=invite123');

    await waitFor(() => {
      expect(screen.getByTestId('confirminvite-page')).toBeInTheDocument();
    });
  });

  it('redirects to confirminvite when user has no prompts and sessionStorage has pending invite', async () => {
    sessionStorage.setItem('pendingInviteCode', 'session-invite');

    vi.mocked(useCurrentUser).mockReturnValue({
      user: {anonymous: false, prompts: [], username: 'testuser'},
      loading: false,
      error: null,
    } as any);

    renderUpdateUser();

    await waitFor(() => {
      expect(screen.getByTestId('confirminvite-page')).toBeInTheDocument();
    });
    expect(sessionStorage.getItem('pendingInviteCode')).toBeNull();
  });

  it('onSuccess redirects to confirminvite when code query param is present', async () => {
    vi.mocked(useCurrentUser).mockReturnValue({
      user: {
        anonymous: false,
        prompts: ['confirm_username'],
        username: 'testuser',
      },
      loading: false,
      error: null,
    } as any);

    renderUpdateUser('?code=query-invite');

    act(() => {
      capturedOnSuccess({prompts: []});
    });

    await waitFor(() => {
      expect(screen.getByTestId('confirminvite-page')).toBeInTheDocument();
    });
  });

  it('onSuccess redirects to confirminvite when sessionStorage has pending invite', async () => {
    sessionStorage.setItem('pendingInviteCode', 'oauth-invite');

    vi.mocked(useCurrentUser).mockReturnValue({
      user: {
        anonymous: false,
        prompts: ['confirm_username'],
        username: 'testuser',
      },
      loading: false,
      error: null,
    } as any);

    renderUpdateUser();

    act(() => {
      capturedOnSuccess({prompts: []});
    });

    await waitFor(() => {
      expect(screen.getByTestId('confirminvite-page')).toBeInTheDocument();
    });
    expect(sessionStorage.getItem('pendingInviteCode')).toBeNull();
  });

  it('redirects to signin when user is anonymous', async () => {
    vi.mocked(useCurrentUser).mockReturnValue({
      user: {anonymous: true, prompts: [], username: ''},
      loading: false,
      error: null,
    } as any);

    renderUpdateUser();

    await waitFor(() => {
      expect(screen.getByTestId('signin-page')).toBeInTheDocument();
    });
  });
});
