import {Banner, Flex, FlexItem, Page} from '@patternfly/react-core';

import {Navigate, Outlet, Route, Routes} from 'react-router-dom';
import {RecoilRoot, useSetRecoilState} from 'recoil';
import {QueryClient, QueryClientProvider} from '@tanstack/react-query';

import useChrome from '@redhat-cloud-services/frontend-components/useChrome';

import {NavigationPath} from './NavigationPath';
import OrganizationsList from './OrganizationsList/OrganizationsList';
import Organization from './OrganizationsList/Organization/Organization';
import RepositoryTagRouter from './RepositoryTagRouter';
import RepositoriesList from './RepositoriesList/RepositoriesList';
import {useEffect, useState, useMemo} from 'react';
import {useQuayConfig} from 'src/hooks/UseQuayConfig';
import NotFound from 'src/components/errors/404';
import {useCurrentUser} from 'src/hooks/UseCurrentUser';
import {InfoCircleIcon} from '@patternfly/react-icons';
import {GlobalAuthState} from '../resources/AuthResource';
import {IsPluginState} from '../atoms/QuayConfigState';
import {CreateNewUser} from 'src/components/modals/CreateNewUser';
import NewUserEmptyPage from 'src/components/NewUserEmptyPage';
import axios from 'axios';
import axiosIns from 'src/libs/axios';
import ManageMembersList from './OrganizationsList/Organization/Tabs/TeamsAndMembership/TeamsView/ManageMembers/ManageMembersList';
import OverviewList from './OverviewList/OverviewList';

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
  const {user, loading, error} = useCurrentUser();

  const setIsPluginState = useSetRecoilState(IsPluginState);
  const [isConfirmUserModalOpen, setConfirmUserModalOpen] = useState(false);

  chrome?.auth?.getToken().then((token) => {
    GlobalAuthState.bearerToken = token;
  });

  useEffect(() => {
    if (quayConfig?.config?.REGISTRY_TITLE) {
      document.title = quayConfig.config.REGISTRY_TITLE;
    }
  }, [quayConfig]);

  useEffect(() => {
    setIsPluginState(true);
    if (user?.prompts && user.prompts.includes('confirm_username')) {
      setConfirmUserModalOpen(true);
    }
  }, [user]);

  if (loading) {
    return null;
  }

  return (
    <Page style={{height: '100vh'}}>
      <CreateNewUser
        user={user}
        isModalOpen={isConfirmUserModalOpen}
        setModalOpen={setConfirmUserModalOpen}
      />
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
      {user?.prompts && user.prompts.includes('confirm_username') ? (
        <NewUserEmptyPage setCreateUserModalOpen={setConfirmUserModalOpen} />
      ) : (
        <Routes>
          <Route index element={<Navigate to="organization" replace />} />
          {NavigationRoutes.map(({path, Component}, key) => (
            <Route path={path} key={key} element={Component} />
          ))}
          <Route path="*" element={<NotFound />} />
        </Routes>
      )}
      <Outlet />
    </Page>
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
