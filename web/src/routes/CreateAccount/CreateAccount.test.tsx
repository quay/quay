import {render, screen} from 'src/test-utils';
import {MemoryRouter, Route, Routes} from 'react-router-dom';
import {CreateAccount} from './CreateAccount';

vi.mock('src/hooks/UseCreateAccount', () => ({
  useCreateAccount: () => ({
    createAccountWithAutoLogin: vi.fn(),
    isLoading: false,
    error: null,
    setError: vi.fn(),
  }),
}));

vi.mock('src/components/LoginPageLayout', () => ({
  LoginPageLayout: ({children}: {children: React.ReactNode}) => (
    <div>{children}</div>
  ),
}));

function renderCreateAccount(search = '') {
  return render(
    <MemoryRouter initialEntries={[`/createaccount${search}`]}>
      <Routes>
        <Route path="/createaccount" element={<CreateAccount />} />
      </Routes>
    </MemoryRouter>,
  );
}

describe('CreateAccount', () => {
  it('shows invite banner when code param is present', () => {
    renderCreateAccount('?code=testinvite123');
    expect(screen.getByTestId('invite-code-alert')).toBeInTheDocument();
    expect(
      screen.getByText("You've been invited to join a team"),
    ).toBeInTheDocument();
  });

  it('does not show invite banner when no code param', () => {
    renderCreateAccount();
    expect(screen.queryByTestId('invite-code-alert')).not.toBeInTheDocument();
  });

  it('preserves invite code in sign-in link', () => {
    renderCreateAccount('?code=mycode');
    const signinLinks = screen.getAllByRole('link', {name: /sign in/i});
    expect(signinLinks.length).toBeGreaterThan(0);
    expect(signinLinks[0]).toHaveAttribute('href', '/signin?code=mycode');
  });

  it('sign-in link has no code param when no invite code', () => {
    renderCreateAccount();
    const signinLinks = screen.getAllByRole('link', {name: /sign in/i});
    expect(signinLinks.length).toBeGreaterThan(0);
    expect(signinLinks[0]).toHaveAttribute('href', '/signin');
  });
});
