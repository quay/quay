import {
  Banner,
  Flex,
  FlexItem,
  NotificationDrawer,
  NotificationDrawerBody,
  NotificationDrawerHeader,
  Page,
} from '@patternfly/react-core';

import {
  Navigate,
  Outlet,
  Route,
  Routes,
  useParams,
  useLocation,
} from 'react-router-dom';

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

/**
 * Interface for shorthand repository route parameters
 */
interface ShorthandParams {
  org: string;
  '*': string;
}

/**
 * Derives reserved route prefixes from NavigationPath enum and additional static routes.
 * These prefixes should NOT be treated as organization names in shorthand repository URLs.
 *
 * @returns Array of reserved path prefixes that won't redirect to repository pages
 */
function getReservedRoutePrefixes(): string[] {
  // Extract first segment from each NavigationPath value
  const navigationPrefixes = Object.values(NavigationPath)
    .map((path) => {
      // Remove leading slash and get first segment
      const segments = path.replace(/^\//, '').split('/');
      return segments[0];
    })
    .filter((prefix) => prefix && !prefix.startsWith(':')); // Filter out empty and param placeholders

  // Additional static routes not in NavigationPath enum
  const staticPrefixes = ['signin', 'createaccount', 'oauth-error'];

  // Combine and deduplicate
  return [...new Set([...navigationPrefixes, ...staticPrefixes])];
}

/**
 * Component to handle shorthand organization and repository URLs.
 *
 * This component provides backward compatibility with the Angular UI's shorthand URL pattern,
 * allowing users to navigate directly to organizations and repositories using shorthand paths.
 *
 * Behavior:
 * - Redirects /:org to /organization/:org (single segment)
 * - Redirects /:org/:repo to /repository/:org/:repo (two or more segments)
 * - Preserves query parameters and hash fragments during redirect
 * - Excludes reserved route prefixes to prevent conflicts with existing routes
 *
 * Reserved prefixes (dynamically derived from NavigationPath):
 * - All first segments from NavigationPath enum (e.g., 'user', 'organization', 'repository', 'overview')
 * - Additional static routes ('signin', 'createaccount', 'oauth-error')
 *
 * @example
 * // Valid organization redirects
 * /myorg → /organization/myorg
 * /projectquay?tab=teams → /organization/projectquay?tab=teams
 *
 * @example
 * // Valid repository redirects
 * /openshift/release → /repository/openshift/release
 * /user1/hello-world?tab=tags#section → /repository/user1/hello-world?tab=tags#section
 *
 * @example
 * // Returns 404 (reserved prefix - passes through to existing routes)
 * /user/testuser → 404 (reserved prefix)
 * /organization/myorg → 404 (reserved prefix)
 * /repository/foo/bar → 404 (reserved prefix)
 */
function RepositoryShorthandRedirect() {
  const params = useParams<ShorthandParams>();
  const location = useLocation();
  const org = params.org;
  const repo = params['*'];

  const reservedPrefixes = getReservedRoutePrefixes();

  // Show 404 if org matches a reserved route prefix (let existing routes handle it)
  if (reservedPrefixes.includes(org)) {
    return <NotFound />;
  }

  // Single segment (/:org) - redirect to organization
  if (!repo || repo.trim() === '') {
    const redirectTo = `/organization/${org}${location.search}${location.hash}`;
    return <Navigate to={redirectTo} replace />;
  }

  // Two or more segments (/:org/:repo) - redirect to repository
  const redirectTo = `/repository/${org}/${repo}${location.search}${location.hash}`;
  return <Navigate to={redirectTo} replace />;
}

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
        <Banner variant="gold">
          <Flex
            spaceItems={{default: 'spaceItemsSm'}}
            justifyContent={{default: 'justifyContentCenter'}}
          >
            <FlexItem>
              <InfoCircleIcon />
            </FlexItem>
            <FlexItem>
              The TLS certificate for cdn01.quay.io is set to be renewed on
              November 17, 2025.{' '}
              <a
                href="https://access.redhat.com/articles/7133408"
                target="_blank"
                rel="noreferrer"
              >
                Learn more
              </a>
              .
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
              {/* Redirect shorthand repository URLs (e.g., /openshift/release) to /repository/openshift/release */}
              <Route path=":org/*" element={<RepositoryShorthandRedirect />} />
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
