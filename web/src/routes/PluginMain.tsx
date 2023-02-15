import {Banner, Flex, FlexItem, Page} from '@patternfly/react-core';

import {Navigate, Outlet, Route, Router, Routes} from 'react-router-dom';
import {RecoilRoot} from 'recoil';
import {QueryClient, QueryClientProvider} from '@tanstack/react-query';

import useChrome from '@redhat-cloud-services/frontend-components/useChrome';

import {NavigationPath} from './NavigationPath';
import OrganizationsList from './OrganizationsList/OrganizationsList';
import Organization from './OrganizationsList/Organization/Organization';
import RepositoryDetails from 'src/routes/RepositoryDetails/RepositoryDetails';
import RepositoriesList from './RepositoriesList/RepositoriesList';
import TagDetails from 'src/routes/TagDetails/TagDetails';
import {useEffect, useMemo} from 'react';
import ErrorBoundary from 'src/components/errors/ErrorBoundary';
import {useQuayConfig} from 'src/hooks/UseQuayConfig';
import SiteUnavailableError from 'src/components/errors/SiteUnavailableError';
import NotFound from 'src/components/errors/404';
import {useCurrentUser} from 'src/hooks/UseCurrentUser';
import {InfoCircleIcon} from '@patternfly/react-icons';
import {GlobalAuthState} from '../resources/AuthResource';

const NavigationRoutes = [
  {
    path: NavigationPath.organizationsList,
    Component: <OrganizationsList />,
  },
  {
    path: NavigationPath.organizationDetail,
    Component: <Organization />,
  },
  {
    path: NavigationPath.repositoriesList,
    Component: <RepositoriesList />,
  },
  {
    path: NavigationPath.repositoryDetail,
    Component: <RepositoryDetails />,
  },
  {
    path: NavigationPath.tagDetail,
    Component: <TagDetails />,
  },
];

function PluginMain() {
  const quayConfig = useQuayConfig();
  const {loading, error} = useCurrentUser();
  const chrome = useChrome();

  console.log('useChrome chrome', chrome);

  chrome?.auth?.getToken().then((token) => {
    console.log('chrome auth token', token);
    GlobalAuthState.bearerToken = token;
  });

  useEffect(() => {
    if (quayConfig?.config?.REGISTRY_TITLE) {
      document.title = quayConfig.config.REGISTRY_TITLE;
    }
  }, [quayConfig]);

  if (loading) {
    return null;
  }

  return (
    <ErrorBoundary hasError={!!error} fallback={<SiteUnavailableError />}>
      <Page style={{height: '100vh'}}>
        <Banner variant="info">
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
                href="https://forms.gle/M2CtyneF3iaMT5UVA"
                target="_blank"
                rel="noreferrer"
              >
                this form
              </a>{' '}
              to provide feedback on your experience
            </FlexItem>
          </Flex>
        </Banner>
        <Routes>
          <Route index element={<Navigate to="organization" replace />} />
          {NavigationRoutes.map(({path, Component}, key) => (
            <Route path={path} key={key} element={Component} />
          ))}
          <Route path="*" element={<NotFound />} />
        </Routes>
        <Outlet />
      </Page>
    </ErrorBoundary>
  );
}

// Wraps the plugin with necessary context providers
export default function PluginMainRoot() {
  // initialize the client only on itial render
  const queryClient = useMemo(() => {
    return new QueryClient({
      defaultOptions: {
        queries: {
          retry: false,
          refetchOnWindowFocus: false,
        },
      },
    });
  }, []);

  return (
    <RecoilRoot>
      <QueryClientProvider client={queryClient}>
        <PluginMain />
      </QueryClientProvider>
    </RecoilRoot>
  );
}
