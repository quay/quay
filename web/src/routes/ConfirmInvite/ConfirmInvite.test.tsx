import {render, screen, waitFor} from 'src/test-utils';
import {MemoryRouter, Route, Routes} from 'react-router-dom';
import {ConfirmInvite} from './ConfirmInvite';
import {acceptTeamInvite} from 'src/resources/TeamResources';
import {useCurrentUser} from 'src/hooks/UseCurrentUser';

vi.mock('src/hooks/UseCurrentUser', () => ({
  useCurrentUser: vi.fn(),
}));

vi.mock('src/hooks/UseQuayConfig', () => ({
  useQuayConfigWithLoading: () => ({isLoading: false, config: {}}),
}));

vi.mock('src/resources/TeamResources', () => ({
  acceptTeamInvite: vi.fn(),
}));

vi.mock('src/components/LoginPageLayout', () => ({
  LoginPageLayout: ({children}: {children: React.ReactNode}) => (
    <div>{children}</div>
  ),
}));

const mockedUseCurrentUser = vi.mocked(useCurrentUser);
const mockedAcceptTeamInvite = vi.mocked(acceptTeamInvite);

const baseUserState = {loading: false, error: undefined, isSuperUser: false};
const anonymousUser = {anonymous: true} as any;
const authenticatedUser = {anonymous: false, username: 'testuser'} as any;

function renderConfirmInvite(search = '?code=testcode123') {
  return render(
    <MemoryRouter initialEntries={[`/confirminvite${search}`]}>
      <Routes>
        <Route path="/confirminvite" element={<ConfirmInvite />} />
        <Route
          path="/organization/:org/teams/:team"
          element={<div>Team Page</div>}
        />
      </Routes>
    </MemoryRouter>,
  );
}

describe('ConfirmInvite', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockedUseCurrentUser.mockReturnValue({
      user: undefined,
      ...baseUserState,
    });
  });

  it('shows error when no code is present in URL', async () => {
    renderConfirmInvite('');
    await waitFor(() => {
      expect(screen.getByTestId('confirm-invite-error')).toBeInTheDocument();
    });
    expect(screen.getByText(/No invite code/i)).toBeInTheDocument();
  });

  it('shows sign-in and create-account buttons for unauthenticated users', async () => {
    mockedUseCurrentUser.mockReturnValue({
      user: anonymousUser,
      ...baseUserState,
    });
    renderConfirmInvite('?code=abc123');
    await waitFor(() => {
      expect(
        screen.getByTestId('confirm-invite-unauthenticated'),
      ).toBeInTheDocument();
    });
    expect(screen.getByTestId('confirm-invite-signin-btn')).toBeInTheDocument();
    expect(
      screen.getByTestId('confirm-invite-create-account-btn'),
    ).toBeInTheDocument();
  });

  it('sign-in button href includes invite code', async () => {
    mockedUseCurrentUser.mockReturnValue({
      user: anonymousUser,
      ...baseUserState,
    });
    renderConfirmInvite('?code=mycode');
    await waitFor(() => {
      expect(
        screen.getByTestId('confirm-invite-signin-btn'),
      ).toBeInTheDocument();
    });
    expect(screen.getByTestId('confirm-invite-signin-btn')).toHaveAttribute(
      'href',
      '/signin?code=mycode',
    );
    expect(
      screen.getByTestId('confirm-invite-create-account-btn'),
    ).toHaveAttribute('href', '/createaccount?code=mycode');
  });

  it('accepts invite and navigates to team page for authenticated users', async () => {
    mockedUseCurrentUser.mockReturnValue({
      user: authenticatedUser,
      ...baseUserState,
    });
    mockedAcceptTeamInvite.mockResolvedValue({org: 'myorg', team: 'myteam'});
    renderConfirmInvite('?code=validcode');
    await waitFor(() => {
      expect(mockedAcceptTeamInvite).toHaveBeenCalledWith('validcode');
    });
    await waitFor(() => {
      expect(screen.getByText('Team Page')).toBeInTheDocument();
    });
  });

  it('shows error when invite acceptance fails', async () => {
    mockedUseCurrentUser.mockReturnValue({
      user: authenticatedUser,
      ...baseUserState,
    });
    mockedAcceptTeamInvite.mockRejectedValue({
      response: {data: {message: 'Invalid invitation code'}},
    });
    renderConfirmInvite('?code=badcode');
    await waitFor(() => {
      expect(screen.getByTestId('confirm-invite-error')).toBeInTheDocument();
    });
    expect(screen.getByText('Invalid invitation code')).toBeInTheDocument();
  });

  it('shows generic error when invite fetch fails with no message', async () => {
    mockedUseCurrentUser.mockReturnValue({
      user: authenticatedUser,
      ...baseUserState,
    });
    mockedAcceptTeamInvite.mockRejectedValue(new Error('Network error'));
    renderConfirmInvite('?code=badcode');
    await waitFor(() => {
      expect(screen.getByTestId('confirm-invite-error')).toBeInTheDocument();
    });
    expect(screen.getByText(/Invalid or expired/i)).toBeInTheDocument();
  });
});
