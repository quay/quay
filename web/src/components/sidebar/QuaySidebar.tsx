import {Nav, NavItem, NavList, PageSidebar} from '@patternfly/react-core';
import {Link, useLocation} from 'react-router-dom';
import {SidebarState} from 'src/atoms/SidebarState';
import {NavigationPath} from 'src/routes/NavigationPath';
import OrganizationsList from 'src/routes/OrganizationsList/OrganizationsList';
import RepositoriesList from 'src/routes/RepositoriesList/RepositoriesList';
import {useRecoilValue} from 'recoil';

interface SideNavProps {
  isSideNav: boolean;
  navPath: NavigationPath;
  title: string;
  component: JSX.Element;
}

const routes: SideNavProps[] = [
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
    component: <RepositoriesList />,
  },
];

export function QuaySidebar() {
  const location = useLocation();
  const sidebarState = useRecoilValue(SidebarState);

  const Navigation = (
    <Nav>
      <NavList>
        {routes.map((route) =>
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
      <PageSidebar className="page-sidebar" theme="dark" nav={Navigation} />
    );
  }
  return <></>;
}
