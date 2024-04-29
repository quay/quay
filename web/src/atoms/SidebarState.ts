import {atom} from 'recoil';

export const SidebarState = atom({
  key: 'sidebarState',
  default: {
    isOpen: true,
  },
});

export const SidebarRoutes = atom({
  key: 'sidebarRoutes',
  default: [],
});
