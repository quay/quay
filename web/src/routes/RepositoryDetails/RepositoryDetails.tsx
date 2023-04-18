import {
  Page,
  PageSection,
  PageSectionVariants,
  Title,
  Tabs,
  Tab,
  TabTitleText,
  Drawer,
  DrawerActions,
  DrawerCloseButton,
  DrawerContent,
  DrawerContentBody,
  DrawerHead,
  DrawerPanelContent,
} from '@patternfly/react-core';
import {QuayBreadcrumb} from 'src/components/breadcrumb/Breadcrumb';
import Tags from './Tags/Tags';
import {useLocation, useSearchParams, useNavigate} from 'react-router-dom';
import {useEffect, useRef, useState} from 'react';
import Settings from './Settings/Settings';
import {DrawerContentType} from './Types';
import AddPermissions from './Settings/PermissionsAddPermission';
import {
  fetchRepositoryDetails,
  RepositoryDetails as IRepositoryDetails,
} from 'src/resources/RepositoryResource';
import ErrorBoundary from 'src/components/errors/ErrorBoundary';
import {addDisplayError, isErrorString} from 'src/resources/ErrorHandling';
import RequestError from 'src/components/errors/RequestError';
import {useQuayConfig} from 'src/hooks/UseQuayConfig';
import CreateNotification from './Settings/NotificationsCreateNotification';
import {useRepository} from 'src/hooks/UseRepository';

enum TabIndex {
  Tags = 'tags',
  Information = 'information',
  TagHistory = 'history',
  Builds = 'builds',
  Logs = 'logs',
  Settings = 'settings',
}

// Return the tab as an enum or null if it does not exist
function getTabIndex(tab: string) {
  if (Object.values(TabIndex).includes(tab as TabIndex)) {
    return tab as TabIndex;
  }
}

export default function RepositoryDetails() {
  const config = useQuayConfig();
  const [activeTabKey, setActiveTabKey] = useState(TabIndex.Tags);
  const navigate = useNavigate();
  const location = useLocation();
  const [searchParams, setSearchParams] = useSearchParams();
  const [drawerContent, setDrawerContent] = useState<DrawerContentType>(
    DrawerContentType.None,
  );
  const [err, setErr] = useState<string>();

  const drawerRef = useRef<HTMLDivElement>();

  // TODO: refactor
  const [organization, ...repo] = location.pathname.split('/').slice(2);
  const repository = repo.join('/');
  const {repoDetails, errorLoadingRepoDetails} = useRepository(
    organization,
    repository,
  );

  const requestedTabIndex = getTabIndex(searchParams.get('tab'));
  if (requestedTabIndex && requestedTabIndex !== activeTabKey) {
    setActiveTabKey(requestedTabIndex);
  }

  function tabsOnSelect(e, tabIndex) {
    navigate(`${location.pathname}?tab=${tabIndex}`);
  }

  const closeDrawer = () => {
    setDrawerContent(DrawerContentType.None);
  };
  const drawerContentOptions = {
    [DrawerContentType.None]: null,
    [DrawerContentType.AddPermission]: (
      <AddPermissions
        org={organization}
        repo={repository}
        closeDrawer={closeDrawer}
      />
    ),
    [DrawerContentType.CreateNotification]: (
      <CreateNotification
        org={organization}
        repo={repository}
        closeDrawer={closeDrawer}
      />
    ),
  };

  useEffect(() => {
    if (errorLoadingRepoDetails) {
      setErr(
        addDisplayError(
          'Unable to get repository',
          errorLoadingRepoDetails as Error,
        ),
      );
    }
  }, [errorLoadingRepoDetails]);

  return (
    <Drawer
      isExpanded={drawerContent != DrawerContentType.None}
      onExpand={() => {
        drawerRef.current && drawerRef.current.focus();
      }}
    >
      <DrawerContent
        panelContent={
          <DrawerPanelContent>
            <DrawerHead>
              <span
                tabIndex={drawerContent != DrawerContentType.None ? 0 : -1}
                ref={drawerRef}
              >
                {drawerContentOptions[drawerContent]}
              </span>
              <DrawerActions>
                <DrawerCloseButton onClick={closeDrawer} />
              </DrawerActions>
            </DrawerHead>
          </DrawerPanelContent>
        }
      >
        <DrawerContentBody>
          <Page>
            <QuayBreadcrumb />
            <PageSection
              variant={PageSectionVariants.light}
              className="no-padding-bottom"
            >
              <Title data-testid="repo-title" headingLevel="h1">
                {repository}
              </Title>
            </PageSection>
            <PageSection
              variant={PageSectionVariants.light}
              className="no-padding-on-sides"
              style={{padding: 0}}
            >
              <ErrorBoundary
                hasError={isErrorString(err)}
                fallback={<RequestError message={err} />}
              >
                <Tabs activeKey={activeTabKey} onSelect={tabsOnSelect}>
                  <Tab
                    eventKey={TabIndex.Tags}
                    title={<TabTitleText>Tags</TabTitleText>}
                  >
                    <Tags
                      organization={organization}
                      repository={repository}
                      repoDetails={repoDetails}
                    />
                  </Tab>
                  <Tab
                    eventKey={TabIndex.Settings}
                    title={<TabTitleText>Settings</TabTitleText>}
                    isHidden={
                      config?.features.UI_V2_REPO_SETTINGS != true ||
                      !repoDetails?.can_admin
                    }
                  >
                    <Settings
                      org={organization}
                      repo={repository}
                      setDrawerContent={setDrawerContent}
                      repoDetails={repoDetails}
                    />
                  </Tab>
                </Tabs>
              </ErrorBoundary>
            </PageSection>
          </Page>
        </DrawerContentBody>
      </DrawerContent>
    </Drawer>
  );
}
