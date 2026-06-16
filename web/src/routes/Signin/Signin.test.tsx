import {render, screen} from 'src/test-utils';
import {MemoryRouter, Route, Routes} from 'react-router-dom';
import {Signin} from './Signin';

const mockFeatures = {
  DIRECT_LOGIN: true,
  INVITE_ONLY_USER_CREATION: false,
  USER_CREATION: true,
  MAILING: true,
};

vi.mock('src/hooks/UseQuayConfig', () => ({
  useQuayConfigWithLoading: () => ({
    isLoading: false,
    config: {
      features: mockFeatures,
      config: {
        AUTHENTICATION_TYPE: 'Database',
      },
    },
  }),
}));

vi.mock('src/hooks/UseQuayState', () => ({
  useQuayState: () => ({inReadOnlyMode: false, inAccountRecoveryMode: false}),
}));

vi.mock('src/hooks/UseExternalLogins', () => ({
  useExternalLogins: () => ({
    externalLogins: [],
    hasExternalLogins: () => false,
    shouldShowDirectLogin: () => true,
    shouldAutoRedirectSSO: () => false,
  }),
}));

vi.mock('src/hooks/UseExternalLoginAuth', () => ({
  useExternalLoginAuth: () => ({
    startExternalLogin: vi.fn(),
    isAuthenticating: false,
    error: null,
  }),
}));

vi.mock('src/hooks/UsePasswordRecovery', () => ({
  usePasswordRecovery: () => ({
    requestRecovery: vi.fn(),
    isLoading: false,
    error: null,
    result: null,
    setError: vi.fn(),
  }),
}));

vi.mock('src/resources/AuthResource', () => ({
  loginUser: vi.fn(),
  GlobalAuthState: {isLoggedIn: false, csrfToken: null, bearerToken: null},
}));

vi.mock('src/resources/UserResource', () => ({
  fetchUser: vi.fn(),
}));

vi.mock('src/libs/axios', () => ({
  getCsrfToken: vi.fn(),
  default: {get: vi.fn(), post: vi.fn()},
}));

vi.mock('src/components/LoginPageLayout', () => ({
  LoginPageLayout: ({children}: {children: React.ReactNode}) => (
    <div>{children}</div>
  ),
}));

vi.mock('src/components/ExternalLoginButton', () => ({
  ExternalLoginButton: () => null,
}));

function renderSignin(search = '') {
  return render(
    <MemoryRouter initialEntries={[`/signin${search}`]}>
      <Routes>
        <Route path="/signin" element={<Signin />} />
      </Routes>
    </MemoryRouter>,
  );
}

describe('Signin', () => {
  beforeEach(() => {
    mockFeatures.DIRECT_LOGIN = true;
    mockFeatures.INVITE_ONLY_USER_CREATION = false;
    mockFeatures.USER_CREATION = true;
    mockFeatures.MAILING = true;
  });

  it('renders login form', () => {
    renderSignin();
    expect(screen.getByText(/Sign in/i)).toBeInTheDocument();
  });

  it('shows create-account link with invite code preserved', () => {
    renderSignin('?code=invitecode123');
    const createAccountLink = screen.getByRole('link', {
      name: /create account/i,
    });
    expect(createAccountLink).toHaveAttribute(
      'href',
      '/createaccount?code=invitecode123',
    );
  });

  it('shows create-account link without code when no invite', () => {
    renderSignin();
    const createAccountLink = screen.getByRole('link', {
      name: /create account/i,
    });
    expect(createAccountLink).toHaveAttribute('href', '/createaccount');
  });

  it('shows invitation message when INVITE_ONLY_USER_CREATION is true and no code', () => {
    mockFeatures.INVITE_ONLY_USER_CREATION = true;
    renderSignin();
    expect(
      screen.getByTestId('signin-invitation-message'),
    ).toBeInTheDocument();
    expect(
      screen.getByText('Invitation required to sign up'),
    ).toBeInTheDocument();
  });

  it('hides create-account link when invite-only and no code', () => {
    mockFeatures.INVITE_ONLY_USER_CREATION = true;
    renderSignin();
    expect(
      screen.queryByRole('link', {name: /create account/i}),
    ).not.toBeInTheDocument();
  });

  it('shows create-account link when invite-only but code is present', () => {
    mockFeatures.INVITE_ONLY_USER_CREATION = true;
    renderSignin('?code=validcode');
    expect(
      screen.getByRole('link', {name: /create account/i}),
    ).toBeInTheDocument();
    expect(
      screen.queryByTestId('signin-invitation-message'),
    ).not.toBeInTheDocument();
  });
});
