import React, { useEffect } from "react";
import { PluginSidebarNavItems } from "src/atoms/SidebarState";
import { useRecoilState } from "recoil";
import { SideNavProps } from "src/components/sidebar/QuaySidebar";
import { PluginNavigationRoutes } from "src/atoms/Routes";
import { NavigationRoute } from "src/routes/NavigationPath";
import { NpmPackagesList } from "./NpmPackagesList";
import RepositoryDetails from "src/routes/RepositoryDetails/RepositoryDetails";

export function init() {
  const [pluginSidebarNavItems, setPluginSidebarNavItems] = useRecoilState<
    SideNavProps[]
  >(PluginSidebarNavItems);
  const [pluginRoutes, setPluginRoutes] = useRecoilState<NavigationRoute[]>(
    PluginNavigationRoutes,
  );
  useEffect(() => {
    // TODO: check if plugin is enabled
    setPluginSidebarNavItems((prevItems) => {
      return [
        ...prevItems,
        {
          isSideNav: true,
          navPath: "npm",
          title: "NPM Packages",
          component: <NpmPackagesList />,
        },
      ] as SideNavProps[];
    });

    setPluginRoutes((prevRoutes) => {
      return [
        ...prevRoutes,
        {
          path: "/npm",
          Component: <NpmPackagesList />,
        },
        {
          path: "/npm/repository",
          Component: <NpmPackagesList />,
        },
        {
          path: "/npm/repository/:organizationName/*",
          Component: <RepositoryDetails />,
        },
      ] as NavigationRoute[];
    });
  }, []);
}
