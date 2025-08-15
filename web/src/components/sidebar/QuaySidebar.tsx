import {
  Nav,
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
import {useCurrentUser} from 'src/hooks/UseCurrentUser';
import ServiceKeys from 'src/routes/Superuser/ServiceKeys/ServiceKeys';
import ChangeLog from 'src/routes/Superuser/ChangeLog/ChangeLog';
import UsageLogs from 'src/routes/Superuser/UsageLogs/UsageLogs';
import Messages from 'src/routes/Superuser/Messages/Messages';

interface SideNavProps {
  isSideNav: boolean;
  navPath: NavigationPath;
  title: string;
  component: JSX.Element;
}

export function QuaySidebar() {
  const location = useLocation();
  const sidebarState = useRecoilValue(SidebarState);
  const quayConfig = useQuayConfig();
  const {isSuperUser} = useCurrentUser();

  const routes: SideNavProps[] = [
    {
      isSideNav: quayConfig?.config?.BRANDING?.quay_io ? true : false,
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
    // Superuser sections
    {
      isSideNav: isSuperUser,
      navPath: NavigationPath.serviceKeys,
      title: 'Service Keys',
      component: <ServiceKeys />,
    },
    {
      isSideNav: isSuperUser,
      navPath: NavigationPath.changeLog,
      title: 'Change Log',
      component: <ChangeLog />,
    },
    {
      isSideNav: isSuperUser,
      navPath: NavigationPath.usageLogs,
      title: 'Usage Logs',
      component: <UsageLogs />,
    },
    {
      isSideNav: isSuperUser,
      navPath: NavigationPath.messages,
      title: 'Messages',
      component: <Messages />,
    },
  ];

  const getTestId = (title: string) => {
    switch (title) {
      case 'Service Keys':
        return 'service-keys-nav';
      case 'Change Log':
        return 'change-log-nav';
      case 'Usage Logs':
        return 'usage-logs-nav';
      case 'Messages':
        return 'messages-nav';
      default:
        return undefined;
    }
  };

  const Navigation = (
    <Nav>
      <NavList>
        {routes.map((route) =>
          route.isSideNav ? (
            <NavItem
              key={route.navPath}
              isActive={location.pathname === route.navPath}
              data-testid={getTestId(route.title)}
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
