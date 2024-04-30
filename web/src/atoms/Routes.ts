import {atom} from 'recoil';

export const NavigationRoutes = atom({
  key: 'routes',
  default: [],
});

export const PluginNavigationRoutes = atom({
  key: 'pluginRoutes',
  default: [],
});
