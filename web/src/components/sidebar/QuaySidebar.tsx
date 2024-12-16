import {
  Nav,
  NavExpandable,
  NavItem,
  NavList,
  PageSidebar,
  PageSidebarBody,
} from '@patternfly/react-core';
import {Link, useLocation} from 'react-router-dom';
import {SidebarState} from 'src/atoms/SidebarState';
import {NavigationPath} from 'src/routes/NavigationPath';
import OrganizationsList from 'src/routes/OrganizationsList/OrganizationsList';
import RepositoriesList from 'src/routes/RepositoriesList/RepositoriesList';
import {useRecoilValue} from 'recoil';
import OverviewList from 'src/routes/OverviewList/OverviewList';
import {useQuayConfig} from 'src/hooks/UseQuayConfig';
import {useState} from 'react';
import SuperuserOrgsList from 'src/routes/SuperuserList/Organizations/SuperuserOrgsList';
import SuperuserUsersList from 'src/routes/SuperuserList/Users/SuperuserUsersList';

interface SideNavProps {
  isSideNav: boolean;
  navPath: NavigationPath;
  title: string;
  component: JSX.Element;
  children?: Array<{
    isSideNav: boolean;
    navPath: string;
    title: string;
    component: React.ReactNode;
  }>;
}

export function QuaySidebar() {
  const location = useLocation();
  const sidebarState = useRecoilValue(SidebarState);
  const quayConfig = useQuayConfig();
  const [activeGroup, setActiveGroup] = useState('nav-expandable-group-1');
  const [activeItem, setActiveItem] = useState('nav-expandable-group-1_item-1');

  const routes: SideNavProps[] = [
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
    {
      isSideNav: true,
      navPath: NavigationPath.superuserUsersList,
      title: 'Superuser',
      component: <SuperuserUsersList />,
      children: [
        {
          isSideNav: false,
          navPath: NavigationPath.superuserUsersList,
          title: 'Users',
          component: <SuperuserUsersList />,
        },
        {
          isSideNav: false,
          navPath: NavigationPath.superuserOrgsList,
          title: 'Organizations',
          component: <SuperuserOrgsList />,
        },
      ],
    },
  ];

  const Navigation = (
    <Nav>
      <NavList>
        {routes.map((route) =>
          route.isSideNav ? (
            route.children ? (
              <NavExpandable
                key={route.navPath}
                title={route.title}
                groupId={route.navPath}
                isActive={location.pathname.startsWith(route.navPath)}
                isExpanded
              >
                {route.children.map((child) => (
                  <NavItem
                    key={child.navPath}
                    isActive={location.pathname === child.navPath}
                  >
                    <Link to={child.navPath}>{child.title}</Link>
                  </NavItem>
                ))}
              </NavExpandable>
            ) : (
              <NavItem
                key={route.navPath}
                isActive={location.pathname === route.navPath}
              >
                <Link to={route.navPath}>{route.title}</Link>
              </NavItem>
            )
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
