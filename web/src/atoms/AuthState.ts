import {atom} from 'recoil';

export const AuthState = atom({
  key: 'authState',
  default: {
    isSignedIn: false,
    csrfToken: null,
    QUAY_OAUTH_TOKEN: '7xahJf2TH8uOZPF1Xya8DkWanOZ75F0MjRX4RnvW',
    QUAY_HOSTNAME:
      'https://skynet-quay-test-harish-ns.apps.hgovinda-ui.quay.devcluster.openshift.com',
  },
});
