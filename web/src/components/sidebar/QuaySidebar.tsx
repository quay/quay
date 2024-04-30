import {
  Nav,
  NavItem,
  NavList,
  PageSidebar,
  PageSidebarBody,
} from '@patternfly/react-core';
import {Link, useLocation} from 'react-router-dom';
import {
  PluginSidebarNavItems,
  SidebarNavItems,
  SidebarState,
} from 'src/atoms/SidebarState';
import {NavigationPath} from 'src/routes/NavigationPath';
import OrganizationsList from 'src/routes/OrganizationsList/OrganizationsList';
import RepositoriesList from 'src/routes/RepositoriesList/RepositoriesList';
import {useRecoilState, useRecoilValue} from 'recoil';
import OverviewList from 'src/routes/OverviewList/OverviewList';
import {useQuayConfig} from 'src/hooks/UseQuayConfig';
import {useEffect} from 'react';

export interface SideNavProps {
  isSideNav: boolean;
  navPath: NavigationPath;
  title: string;
  component: JSX.Element;
}

export function QuaySidebar() {
  const location = useLocation();
  const sidebarState = useRecoilValue(SidebarState);
  const quayConfig = useQuayConfig();
  const pluginSidebarNavItems = useRecoilValue(PluginSidebarNavItems);
  const [sidebarNavItems, setSidebarNavItems] =
    useRecoilState<SideNavProps[]>(SidebarNavItems);

  useEffect(() => {
    // default sidebar routes
    setSidebarNavItems([
      {
        isSideNav: quayConfig?.config?.BRANDING.quay_io ? true : false,
        navPath: NavigationPath.overviewList,
        title: 'Overview',
        component: <OverviewList />,
      },
      {
        isSideNav: true,
        navPath: NavigationPath.organizationsList,
        title: 'Organizations',
        component: <OrganizationsList />,
      },
      {
        isSideNav: true,
        navPath: NavigationPath.repositoriesList,
        title: 'Repositories',
        component: <RepositoriesList organizationName={null} />,
      },
    ]);
  }, []);

  useEffect(() => {
    // merge with plugin sidebar routes
    setSidebarNavItems((prevNavItems) => [
      ...prevNavItems,
      ...pluginSidebarNavItems,
    ]);
  }, [pluginSidebarNavItems]);

  const Navigation = (
    <Nav>
      <NavList>
        {sidebarNavItems.map((route) =>
          route.isSideNav ? (
            <NavItem
              key={route.navPath}
              isActive={location.pathname === route.navPath}
            >
              <Link to={route.navPath}>{route.title}</Link>
            </NavItem>
          ) : null,
        )}
      </NavList>
    </Nav>
  );

  if (sidebarState.isOpen) {
    return (
      <PageSidebar className="page-sidebar" theme="dark">
        <PageSidebarBody>{Navigation}</PageSidebarBody>
      </PageSidebar>
    );
  }
  return <></>;
}
