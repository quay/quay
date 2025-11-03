import {
  Banner,
  Flex,
  FlexItem,
  NotificationDrawer,
  NotificationDrawerBody,
  NotificationDrawerHeader,
  Page,
} from '@patternfly/react-core';

import {Navigate, Outlet, Route, Routes} from 'react-router-dom';

import {QuayHeader} from 'src/components/header/QuayHeader';
import {QuaySidebar} from 'src/components/sidebar/QuaySidebar';
import {QuayFooter} from 'src/components/footer/QuayFooter';
import {NavigationPath} from './NavigationPath';

import {useEffect, useState, lazy, Suspense} from 'react';
import ErrorBoundary from 'src/components/errors/ErrorBoundary';
import {useQuayConfig} from 'src/hooks/UseQuayConfig';
import SiteUnavailableError from 'src/components/errors/SiteUnavailableError';
import NotFound from 'src/components/errors/404';
import {useCurrentUser} from 'src/hooks/UseCurrentUser';
import {InfoCircleIcon} from '@patternfly/react-icons';
import axios from 'axios';
import axiosIns from 'src/libs/axios';
import Alerts from './Alerts';
import Conditional from 'src/components/empty/Conditional';
import RegistryStatus from './RegistryStatus';
import {NotificationDrawerListComponent} from 'src/components/notifications/NotificationDrawerList';
import {OAuthError} from 'src/routes/OAuthCallback/OAuthError';
import SystemStatusBanner from 'src/components/SystemStatusBanner';
import {GlobalMessages} from 'src/components/GlobalMessages';
import {LoadingPage} from 'src/components/LoadingPage';

// Lazy load route components for better performance
const OrganizationsList = lazy(
  () => import('./OrganizationsList/OrganizationsList'),
);
const Organization = lazy(
  () => import('./OrganizationsList/Organization/Organization'),
);
const RepositoriesList = lazy(
  () => import('./RepositoriesList/RepositoriesList'),
);
const RepositoryTagRouter = lazy(() => import('./RepositoryTagRouter'));
const OverviewList = lazy(() => import('./OverviewList/OverviewList'));
const SetupBuildTriggerRedirect = lazy(
  () => import('./SetupBuildtrigger/SetupBuildTriggerRedirect'),
);
const ServiceKeys = lazy(() => import('./Superuser/ServiceKeys/ServiceKeys'));
const ChangeLog = lazy(() => import('./Superuser/ChangeLog/ChangeLog'));
const UsageLogs = lazy(() => import('./Superuser/UsageLogs/UsageLogs'));
const Messages = lazy(() => import('./Superuser/Messages/Messages'));
const BuildLogs = lazy(() => import('./Superuser/BuildLogs/BuildLogs'));

const NavigationRoutes = [
  {
    path: NavigationPath.teamMember,
    Component: <Organization />,
  },
  {
    path: NavigationPath.overviewList,
    Component: <OverviewList />,
  },
  {
    path: NavigationPath.organizationsList,
    Component: <OrganizationsList />,
  },
  {
    path: NavigationPath.organizationDetail,
    Component: <Organization />,
  },
  {
    path: NavigationPath.userDetail,
    Component: <Organization />,
  },
  {
    path: NavigationPath.repositoriesList,
    Component: <RepositoriesList organizationName={null} />,
  },
  {
    path: NavigationPath.setupBuildTrigger,
    Component: <SetupBuildTriggerRedirect />,
  },
  {
    path: NavigationPath.repositoryDetail,
    Component: <RepositoryTagRouter />,
  },
  // Superuser routes
  {
    path: NavigationPath.serviceKeys,
    Component: <ServiceKeys />,
  },
  {
    path: NavigationPath.changeLog,
    Component: <ChangeLog />,
  },
  {
    path: NavigationPath.usageLogs,
    Component: <UsageLogs />,
  },
  {
    path: NavigationPath.messages,
    Component: <Messages />,
  },
  {
    path: NavigationPath.buildLogs,
    Component: <BuildLogs />,
  },
];

export function StandaloneMain() {
  axios.defaults.baseURL =
    process.env.REACT_QUAY_APP_API_URL ||
    `${window.location.protocol}//${window.location.host}`;
  axiosIns.defaults.baseURL = axios.defaults.baseURL;

  const quayConfig = useQuayConfig();
  const {loading, error} = useCurrentUser();

  const [isDrawerOpen, setIsDrawerOpen] = useState(false);

  const toggleDrawer = () => {
    setIsDrawerOpen((prev) => !prev);
  };

  const notificationDrawer = (
    <NotificationDrawer>
      <NotificationDrawerHeader title="Notifications" onClose={toggleDrawer} />
      <NotificationDrawerBody>
        <NotificationDrawerListComponent />
      </NotificationDrawerBody>
    </NotificationDrawer>
  );

  useEffect(() => {
    if (quayConfig?.config?.REGISTRY_TITLE) {
      document.title = `${quayConfig.config.REGISTRY_TITLE} • Quay`;
    }
  }, [quayConfig]);

  if (loading) {
    return null;
  }
  return (
    <ErrorBoundary hasError={!!error} fallback={<SiteUnavailableError />}>
      <Page
        header={<QuayHeader toggleDrawer={toggleDrawer} />}
        sidebar={<QuaySidebar />}
        isManagedSidebar
        defaultManagedSidebarIsOpen={true}
        notificationDrawer={notificationDrawer}
        isNotificationDrawerExpanded={isDrawerOpen}
      >
        <Banner variant="blue">
          <Flex
            spaceItems={{default: 'spaceItemsSm'}}
            justifyContent={{default: 'justifyContentCenter'}}
          >
            <FlexItem>
              <InfoCircleIcon />
            </FlexItem>
            <FlexItem>
              Please use{' '}
              <a
                href={quayConfig?.config?.UI_V2_FEEDBACK_FORM}
                target="_blank"
                rel="noreferrer"
              >
                this form
              </a>{' '}
              to provide feedback on your experience
            </FlexItem>
          </Flex>
        </Banner>
        <SystemStatusBanner />
        <GlobalMessages />
        <Conditional if={quayConfig?.features?.BILLING}>
          <ErrorBoundary fallback={<>Error loading registry status</>}>
            <RegistryStatus />
          </ErrorBoundary>
        </Conditional>
        <Alerts />
        <div style={{flex: 1, display: 'flex', flexDirection: 'column'}}>
          <Suspense fallback={<LoadingPage />}>
            <Routes>
              <Route index element={<Navigate to="/organization" replace />} />
              {NavigationRoutes.map(({path, Component}, key) => (
                <Route path={path} key={key} element={Component} />
              ))}
              <Route path="oauth-error" element={<OAuthError />} />
              <Route path="*" element={<NotFound />} />
            </Routes>
          </Suspense>
          <Outlet />
        </div>
        <QuayFooter />
      </Page>
    </ErrorBoundary>
  );
}
