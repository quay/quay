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
import {useCurrentUser} from 'src/hooks/UseCurrentUser';
import ServiceKeys from 'src/routes/Superuser/ServiceKeys/ServiceKeys';
import ChangeLog from 'src/routes/Superuser/ChangeLog/ChangeLog';
import UsageLogs from 'src/routes/Superuser/UsageLogs/UsageLogs';
import Messages from 'src/routes/Superuser/Messages/Messages';
import React from 'react';

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

  // State to track if Superuser section is expanded
  const [isSuperuserExpanded, setIsSuperuserExpanded] = React.useState(false);

  // Auto-expand Superuser section if currently on a superuser route
  React.useEffect(() => {
    const superuserPaths = [
      NavigationPath.serviceKeys,
      NavigationPath.changeLog,
      NavigationPath.usageLogs,
      NavigationPath.messages,
      ...(quayConfig?.config?.BUILD_SUPPORT ? [NavigationPath.buildLogs] : []),
    ];

    if (superuserPaths.includes(location.pathname as NavigationPath)) {
      setIsSuperuserExpanded(true);
    }
  }, [location.pathname]);

  // Regular navigation routes
  const regularRoutes: SideNavProps[] = [
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
  ];

  // Superuser navigation routes
  const superuserRoutes: SideNavProps[] = [
    {
      isSideNav: true,
      navPath: NavigationPath.serviceKeys,
      title: 'Service Keys',
      component: <ServiceKeys />,
    },
    {
      isSideNav: true,
      navPath: NavigationPath.changeLog,
      title: 'Change Log',
      component: <ChangeLog />,
    },
    {
      isSideNav: true,
      navPath: NavigationPath.usageLogs,
      title: 'Usage Logs',
      component: <UsageLogs />,
    },
    {
      isSideNav: true,
      navPath: NavigationPath.messages,
      title: 'Messages',
      component: <Messages />,
    },
    // Conditional Build Logs (if BUILD_SUPPORT enabled)
    ...(quayConfig?.config?.BUILD_SUPPORT
      ? [
          {
            isSideNav: true,
            navPath: NavigationPath.buildLogs,
            title: 'Build Logs',
            component: <></>, // TODO: Implement BuildLogs component
          },
        ]
      : []),
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
      case 'Build Logs':
        return 'build-logs-nav';
      default:
        return undefined;
    }
  };

  const Navigation = (
    <Nav>
      <NavList>
        {/* Regular navigation items */}
        {regularRoutes.map((route) =>
          route.isSideNav ? (
            <NavItem
              key={route.navPath}
              isActive={location.pathname === route.navPath}
            >
              <Link to={route.navPath}>{route.title}</Link>
            </NavItem>
          ) : null,
        )}

        {/* Superuser expandable section */}
        {isSuperUser && (
          <NavExpandable
            title="Superuser"
            isExpanded={isSuperuserExpanded}
            onExpand={() => setIsSuperuserExpanded(!isSuperuserExpanded)}
            isActive={superuserRoutes.some(
              (route) => location.pathname === route.navPath,
            )}
            data-testid="superuser-nav"
          >
            {superuserRoutes.map((route) =>
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
          </NavExpandable>
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
