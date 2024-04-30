import {atom, RecoilState} from 'recoil';
import {SideNavProps} from 'src/components/sidebar/QuaySidebar';

export const SidebarState = atom({
  key: 'sidebarState',
  default: {
    isOpen: true,
  },
});

export const SidebarNavItems: RecoilState<SideNavProps[]> = atom({
  key: 'sidebarNavItems',
  default: [],
});

export const PluginSidebarNavItems: RecoilState<SideNavProps[]> = atom({
  key: 'pluginSidebarNavItems',
  default: [],
});
