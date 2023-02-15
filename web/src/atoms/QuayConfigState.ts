import {atom} from 'recoil';

export const QuayConfigState = atom({
  key: 'quayConfigState',
  default: null,
});

export const IsPluginState = atom({
  key: 'isPlugin',
  default: false,
});
