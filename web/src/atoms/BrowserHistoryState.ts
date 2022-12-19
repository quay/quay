import {atom} from 'recoil';
import {recoilPersist} from 'recoil-persist';

const {persistAtom} = recoilPersist();

export const BrowserHistoryState = atom({
  key: 'browserHistoryState',
  default: [],
  effects_UNSTABLE: [persistAtom],
});
