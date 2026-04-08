import {atom} from 'recoil';

export const AuthState = atom({
  key: 'authState',
  default: {
    isSignedIn: false,
    csrfToken: null,
  },
});
