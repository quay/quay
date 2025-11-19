import {Banner, Flex, FlexItem, Page} from '@patternfly/react-core';

import {Navigate, Outlet, Route, Routes} from 'react-router-dom';
import {RecoilRoot} from 'recoil';
import {QueryClient, QueryClientProvider} from '@tanstack/react-query';

import useChrome from '@redhat-cloud-services/frontend-components/useChrome';

import {NavigationPath} from './NavigationPath';
import {useEffect, useState, useMemo, lazy, Suspense} from 'react';
import {useQuayConfig} from 'src/hooks/UseQuayConfig';
import NotFound from 'src/components/errors/404';
import {useCurrentUser} from 'src/hooks/UseCurrentUser';
import {InfoCircleIcon} from '@patternfly/react-icons';
import {GlobalAuthState} from '../resources/AuthResource';
import {CreateNewUser} from 'src/components/modals/CreateNewUser';
import NewUserEmptyPage from 'src/components/NewUserEmptyPage';
import axios from 'axios';
import axiosIns from 'src/libs/axios';
import {LoadingPage} from 'src/components/LoadingPage';
import SystemStatusBanner from 'src/components/SystemStatusBanner';

// Lazy load route components for better performance
const OrganizationsList = lazy(
  () => import('./OrganizationsList/OrganizationsList'),
);
const Organization = lazy(
  () => import('./OrganizationsList/Organization/Organization'),
);
const RepositoryTagRouter = lazy(() => import('./RepositoryTagRouter'));
const RepositoriesList = lazy(
  () => import('./RepositoriesList/RepositoriesList'),
);
const ManageMembersList = lazy(
  () =>
    import(
      './OrganizationsList/Organization/Tabs/TeamsAndMembership/TeamsView/ManageMembers/ManageMembersList'
    ),
);
const OverviewList = lazy(() => import('./OverviewList/OverviewList'));

const NavigationRoutes = [
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
    path: NavigationPath.repositoriesList,
    Component: <RepositoriesList organizationName={null} />,
  },
  {
    path: NavigationPath.repositoryDetail,
    Component: <RepositoryTagRouter />,
  },
  {
    path: NavigationPath.teamMember,
    Component: <ManageMembersList />,
  },
];

function PluginMain() {
  const chrome = useChrome();
  if (!chrome) {
    return null;
  }

  if (chrome?.isProd()) {
    axios.defaults.baseURL = 'https://quay.io';
    axiosIns.defaults.baseURL = 'https://quay.io';
  } else {
    axios.defaults.baseURL = 'https://stage.quay.io';
    axiosIns.defaults.baseURL = 'https://stage.quay.io';
  }

  const quayConfig = useQuayConfig();
  const [isConfirmUserModalOpen, setConfirmUserModalOpen] = useState(false);
  const [tokenReady, setTokenReady] = useState(false);

  useEffect(() => {
    chrome?.auth?.getToken().then((token) => {
      GlobalAuthState.bearerToken = token;
      setTokenReady(true);
    });
  }, []);

  const {user, loading} = useCurrentUser(tokenReady);

  useEffect(() => {
    if (quayConfig?.config?.REGISTRY_TITLE) {
      document.title = quayConfig.config.REGISTRY_TITLE;
    }
  }, [quayConfig]);

  useEffect(() => {
    if (user?.prompts && user.prompts.includes('confirm_username')) {
      setConfirmUserModalOpen(true);
    }
  }, [user]);

  if (!tokenReady || loading) {
    return <LoadingPage />;
  }

  return (
    <Page style={{height: '100vh'}}>
      {!user && (
        <Banner variant="gold">
          <Flex
            spaceItems={{default: 'spaceItemsSm'}}
            justifyContent={{default: 'justifyContentCenter'}}
          >
            <FlexItem>
              <InfoCircleIcon />
            </FlexItem>
            <FlexItem>
              We are currently experiencing authentication issues with RH SSO.
              Our team is actively investigating this issue and working to
              restore authentication.
            </FlexItem>
          </Flex>
        </Banner>
      )}
      {quayConfig?.config?.UI_V2_FEEDBACK_FORM && (
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
      )}
      <SystemStatusBanner />
      {user && (
        <CreateNewUser
          user={user}
          isModalOpen={isConfirmUserModalOpen}
          setModalOpen={setConfirmUserModalOpen}
        />
      )}
      {user?.prompts && user.prompts.includes('confirm_username') ? (
        <NewUserEmptyPage setCreateUserModalOpen={setConfirmUserModalOpen} />
      ) : (
        <Suspense fallback={<LoadingPage />}>
          <Routes>
            <Route index element={<Navigate to="organization" replace />} />
            {NavigationRoutes.map(({path, Component}, key) => (
              <Route path={path} key={key} element={Component} />
            ))}
            <Route path="*" element={<NotFound />} />
          </Routes>
        </Suspense>
      )}
      <Outlet />
    </Page>
  );
}

// Wraps the plugin with necessary context providers
export default function PluginMainRoot() {
  // initialize the client only on initial render
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
