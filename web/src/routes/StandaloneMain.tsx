import {Banner, Flex, FlexItem, Page} from '@patternfly/react-core';

import {Navigate, Outlet, Route, Routes} from 'react-router-dom';

import {QuayHeader} from 'src/components/header/QuayHeader';
import {QuaySidebar} from 'src/components/sidebar/QuaySidebar';
import { NavigationPath, NavigationRoute } from './NavigationPath';
import OrganizationsList from './OrganizationsList/OrganizationsList';
import Organization from './OrganizationsList/Organization/Organization';
import RepositoriesList from './RepositoriesList/RepositoriesList';
import RepositoryTagRouter from './RepositoryTagRouter';

import {useEffect, useState} from 'react';
import ErrorBoundary from 'src/components/errors/ErrorBoundary';
import {useQuayConfig} from 'src/hooks/UseQuayConfig';
import SiteUnavailableError from 'src/components/errors/SiteUnavailableError';
import NotFound from 'src/components/errors/404';
import {useCurrentUser} from 'src/hooks/UseCurrentUser';
import {InfoCircleIcon} from '@patternfly/react-icons';
import axios from 'axios';
import axiosIns from 'src/libs/axios';
import Alerts from './Alerts';
import OverviewList from './OverviewList/OverviewList';
import SetupBuildTriggerRedirect from './SetupBuildtrigger/SetupBuildTriggerRedirect';
import Conditional from 'src/components/empty/Conditional';
import RegistryStatus from './RegistryStatus';
import {useRecoilState} from 'recoil';
import {NavigationRoutes, PluginNavigationRoutes} from 'src/atoms/Routes';

const DefaultNavigationRoutes = [
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
];

export function StandaloneMain() {
  axios.defaults.baseURL =
    process.env.REACT_QUAY_APP_API_URL ||
    `${window.location.protocol}//${window.location.host}`;
  axiosIns.defaults.baseURL = axios.defaults.baseURL;

  const quayConfig = useQuayConfig();
  const [navRoutes, setNavRoutes] =
    useRecoilState<NavigationRoute[]>(NavigationRoutes);
  const [pluginRoutes] = useRecoilState<NavigationRoute[]>(
    PluginNavigationRoutes,
  );
  const {loading, error} = useCurrentUser();

  useEffect(() => {
    setNavRoutes(DefaultNavigationRoutes);
  }, []);

  useEffect(() => {
    setNavRoutes((prevNavRoutes) => [...prevNavRoutes, ...pluginRoutes]);
  }, [pluginRoutes]);

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
      <Page
        header={<QuayHeader />}
        sidebar={<QuaySidebar />}
        style={{height: '100vh'}}
        isManagedSidebar
        defaultManagedSidebarIsOpen={true}
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
        <Conditional if={quayConfig?.features?.BILLING}>
          <ErrorBoundary fallback={<>Error loading registry status</>}>
            <RegistryStatus />
          </ErrorBoundary>
        </Conditional>
        <Alerts />
        <Routes>
          <Route index element={<Navigate to="/organization" replace />} />
          {navRoutes.map(({path, Component}, key) => (
            <Route path={path} key={key} element={Component} />
          ))}
          <Route path="*" element={<NotFound />} />
        </Routes>
        <Outlet />
      </Page>
    </ErrorBoundary>
  );
}
