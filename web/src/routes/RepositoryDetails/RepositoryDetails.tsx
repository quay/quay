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
import TagsList from './Tags/TagsList';
import {useLocation, useSearchParams, useNavigate} from 'react-router-dom';
import {useEffect, useRef, useState} from 'react';
import Settings from './Settings/Settings';
import {DrawerContentType} from './Types';
import AddPermissions from './Settings/PermissionsAddPermission';
import ErrorBoundary from 'src/components/errors/ErrorBoundary';
import {addDisplayError, isErrorString} from 'src/resources/ErrorHandling';
import RequestError from 'src/components/errors/RequestError';
import {useQuayConfig} from 'src/hooks/UseQuayConfig';
import CreateNotification from './Settings/NotificationsCreateNotification';
import {useRepository} from 'src/hooks/UseRepository';
import {
  parseOrgNameFromUrl,
  parseRepoNameFromUrl,
  validateTeamName,
} from 'src/libs/utils';
import TagHistory from './TagHistory/TagHistory';
import Conditional from 'src/components/empty/Conditional';
import CreateRobotAccountModal from 'src/components/modals/CreateRobotAccountModal';
import {RepoPermissionDropdownItems} from '../RepositoriesList/RobotAccountsList';
import {Entity} from 'src/resources/UserResource';
import {useFetchTeams} from 'src/hooks/UseTeams';
import {CreateTeamModal} from '../OrganizationsList/Organization/Tabs/DefaultPermissions/createPermissionDrawer/CreateTeamModal';
import {useAlerts} from 'src/hooks/UseAlerts';
import {AlertVariant} from 'src/atoms/AlertState';
import Builds from './Builds/Builds';

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
  const [isCreateRobotModalOpen, setIsCreateRobotModalOpen] = useState(false);
  const [selectedEntity, setSelectedEntity] = useState<Entity>(null);
  const {addAlert} = useAlerts();
  const [err, setErr] = useState<string>();

  const drawerRef = useRef<HTMLDivElement>();

  const organization = parseOrgNameFromUrl(location.pathname);
  const repository = parseRepoNameFromUrl(location.pathname);
  const {repoDetails, errorLoadingRepoDetails} = useRepository(
    organization,
    repository,
  );

  // state variables for Create Team
  const [teamName, setTeamName] = useState('');
  const [teamDescription, setTeamDescription] = useState('');
  const [isTeamModalOpen, setIsTeamModalOpen] = useState<boolean>(false);

  const {teams} = useFetchTeams(organization);
  const setupBuildTriggerUuid = searchParams.get('setupTrigger');

  const createRobotModal = (
    <CreateRobotAccountModal
      isModalOpen={isCreateRobotModalOpen}
      handleModalToggle={() =>
        setIsCreateRobotModalOpen(!isCreateRobotModalOpen)
      }
      orgName={organization}
      teams={teams}
      RepoPermissionDropdownItems={RepoPermissionDropdownItems}
      setEntity={setSelectedEntity}
      showSuccessAlert={(message) =>
        addAlert({
          variant: AlertVariant.Success,
          title: message,
        })
      }
      showErrorAlert={(message) =>
        addAlert({
          variant: AlertVariant.Failure,
          title: message,
        })
      }
    />
  );

  const createTeamModal = (
    <CreateTeamModal
      teamName={teamName}
      setTeamName={setTeamName}
      description={teamDescription}
      setDescription={setTeamDescription}
      orgName={organization}
      nameLabel="Provide a name for your new team:"
      descriptionLabel="Provide an optional description for your new team"
      helperText="Enter a description to provide extra information to your teammates about this team:"
      nameHelperText="Choose a name to inform your teammates about this team. Must match ^[a-z][a-z0-9]+$."
      isModalOpen={isTeamModalOpen}
      handleModalToggle={() => setIsTeamModalOpen(!isTeamModalOpen)}
      validateName={validateTeamName}
      setAppliedTo={setSelectedEntity}
    ></CreateTeamModal>
  );

  const requestedTabIndex = getTabIndex(searchParams.get('tab'));
  if (requestedTabIndex && requestedTabIndex !== activeTabKey) {
    setActiveTabKey(requestedTabIndex);
  }

  function tabsOnSelect(e, tabIndex) {
    navigate(`${location.pathname}?tab=${tabIndex}`);
  }

  const closeDrawer = () => {
    setSelectedEntity(null);
    setDrawerContent(DrawerContentType.None);
  };

  const drawerContentOptions = {
    [DrawerContentType.None]: null,
    [DrawerContentType.AddPermission]: (
      <AddPermissions
        org={organization}
        repo={repository}
        teams={teams}
        closeDrawer={closeDrawer}
        isCreateRobotModalOpen={isCreateRobotModalOpen}
        setIsCreateRobotModalOpen={setIsCreateRobotModalOpen}
        isTeamModalOpen={isTeamModalOpen}
        setIsTeamModalOpen={setIsTeamModalOpen}
        selectedEntity={selectedEntity}
        setSelectedEntity={setSelectedEntity}
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
    <>
      <Conditional if={isCreateRobotModalOpen}>{createRobotModal}</Conditional>
      <Conditional if={isTeamModalOpen}>{createTeamModal}</Conditional>
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
                  <Tabs
                    mountOnEnter
                    unmountOnExit
                    activeKey={activeTabKey}
                    onSelect={tabsOnSelect}
                  >
                    <Tab
                      eventKey={TabIndex.Tags}
                      title={<TabTitleText>Tags</TabTitleText>}
                    >
                      <TagsList
                        organization={organization}
                        repository={repository}
                        repoDetails={repoDetails}
                      />
                    </Tab>
                    <Tab
                      eventKey={TabIndex.TagHistory}
                      title={<TabTitleText>Tag history</TabTitleText>}
                    >
                      <TagHistory
                        org={organization}
                        repo={repository}
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
                    <Tab
                      eventKey={TabIndex.Builds}
                      title={<TabTitleText>Builds</TabTitleText>}
                      isHidden={
                        config?.features.UI_V2_BUILDS != true ||
                        config?.features.BUILD_SUPPORT != true ||
                        !repoDetails?.can_write
                      }
                    >
                      <Builds
                        org={organization}
                        repo={repository}
                        setupTriggerUuid={setupBuildTriggerUuid}
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
    </>
  );
}
