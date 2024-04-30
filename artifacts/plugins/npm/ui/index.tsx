import { useEffect } from "react";
import { PluginSidebarNavItems } from "src/atoms/SidebarState";
import { useRecoilState } from "recoil";
import { SideNavProps } from "src/components/sidebar/QuaySidebar";
import { PluginNavigationRoutes } from "src/atoms/Routes";
import { NavigationRoute } from "src/routes/NavigationPath";
import RepositoriesList from "src/routes/RepositoriesList/RepositoriesList";

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
          component: <NpmPlugin />,
        },
      ] as SideNavProps[];
    });

    setPluginRoutes((prevRoutes) => {
      return [
        ...prevRoutes,
        {
          path: "/npm",
          Component: <NpmPlugin />,
        },
      ] as NavigationRoute[];
    });
  }, []);
}

function NpmPlugin() {
  return (
    <>
      <RepositoriesList organizationName={null} title={"NPM Packages"} />
    </>
  );
}
