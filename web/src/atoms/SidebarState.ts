import {atom} from 'recoil';

export const SidebarState = atom({
  key: 'sidebarState',
  default: {
    isOpen: true,
  },
});
