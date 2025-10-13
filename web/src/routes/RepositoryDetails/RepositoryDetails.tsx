import {
  Drawer,
  DrawerActions,
  DrawerCloseButton,
  DrawerContent,
  DrawerContentBody,
  DrawerHead,
  DrawerPanelContent,
  PageSection,
  Tab,
  TabTitleText,
  Tabs,
  Title,
} from '@patternfly/react-core';
import {useEffect, useRef, useState} from 'react';
import {useLocation, useNavigate, useSearchParams} from 'react-router-dom';
import {AlertVariant} from 'src/atoms/AlertState';
import {QuayBreadcrumb} from 'src/components/breadcrumb/Breadcrumb';
import Conditional from 'src/components/empty/Conditional';
import ErrorBoundary from 'src/components/errors/ErrorBoundary';
import RequestError from 'src/components/errors/RequestError';
import CreateRobotAccountModal from 'src/components/modals/CreateRobotAccountModal';
import {useAlerts} from 'src/hooks/UseAlerts';
import {useQuayConfig} from 'src/hooks/UseQuayConfig';
import {useRepository} from 'src/hooks/UseRepository';
import {useFetchTeams} from 'src/hooks/UseTeams';
import {
  parseOrgNameFromUrl,
  parseRepoNameFromUrl,
  validateTeamName,
} from 'src/libs/utils';
import {addDisplayError, isErrorString} from 'src/resources/ErrorHandling';
import {Entity} from 'src/resources/UserResource';
import {CreateTeamModal} from '../OrganizationsList/Organization/Tabs/DefaultPermissions/createPermissionDrawer/CreateTeamModal';
import {RepoPermissionDropdownItems} from '../RepositoriesList/RobotAccountsList';
import Builds from './Builds/Builds';
import CreateNotification from './Settings/NotificationsCreateNotification';
import AddPermissions from './Settings/PermissionsAddPermission';
import Settings from './Settings/Settings';
import TagHistory from './TagHistory/TagHistory';
import TagsList from './Tags/TagsList';
import {DrawerContentType} from './Types';
import UsageLogs from '../UsageLogs/UsageLogs';
import {Mirroring} from './Mirroring/Mirroring';

enum TabIndex {
  Tags = 'tags',
  Information = 'information',
  TagHistory = 'history',
  Builds = 'builds',
  Logs = 'logs',
  Mirroring = 'mirroring',
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
  const [searchParams] = useSearchParams();
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
      nameHelperText="Choose a name to inform your teammates about this team. Must match ^([a-z0-9]+(?:[._-][a-z0-9]+)*)$"
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
            <QuayBreadcrumb />
            <PageSection hasBodyWrapper={false}>
              <Title data-testid="repo-title" headingLevel="h1">
                {repository}
              </Title>
            </PageSection>
            <PageSection
              hasBodyWrapper={false}
              padding={{default: 'noPadding'}}
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
                  usePageInsets={true}
                >
                  <Tab
                    eventKey={TabIndex.Tags}
                    title={<TabTitleText>Tags</TabTitleText>}
                    onPointerEnterCapture={undefined}
                    onPointerLeaveCapture={undefined}
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
                    onPointerEnterCapture={undefined}
                    onPointerLeaveCapture={undefined}
                  >
                    <TagHistory
                      org={organization}
                      repo={repository}
                      repoDetails={repoDetails}
                    />
                  </Tab>
                  <Tab
                    eventKey={TabIndex.Logs}
                    title={<TabTitleText>Logs</TabTitleText>}
                    onPointerEnterCapture={undefined}
                    onPointerLeaveCapture={undefined}
                  >
                    <UsageLogs
                      organization={organization}
                      repository={repository}
                      type="repository"
                    />
                  </Tab>
                  <Tab
                    eventKey={TabIndex.Mirroring}
                    title={<TabTitleText>Mirroring</TabTitleText>}
                    data-testid="mirroring-tab"
                    isHidden={
                      !config?.features?.REPO_MIRROR || !repoDetails?.can_admin
                    }
                    onPointerEnterCapture={undefined}
                    onPointerLeaveCapture={undefined}
                  >
                    {repoDetails?.state !== 'MIRROR' ? (
                      <div>
                        This repository&apos;s state is{' '}
                        <strong>{repoDetails?.state}</strong>. Use the{' '}
                        <a
                          href={`/repository/${repoDetails?.namespace}/${repoDetails?.name}?tab=settings`}
                        >
                          Settings tab
                        </a>{' '}
                        and change it to <strong>Mirror</strong> to manage its
                        mirroring configuration.
                      </div>
                    ) : (
                      <Mirroring
                        namespace={organization}
                        repoName={repository}
                      />
                    )}
                  </Tab>
                  <Tab
                    eventKey={TabIndex.Builds}
                    title={<TabTitleText>Builds</TabTitleText>}
                    isHidden={
                      config?.features.BUILD_SUPPORT != true ||
                      repoDetails?.state !== 'NORMAL' ||
                      (!repoDetails?.can_write && !repoDetails?.can_admin)
                    }
                    onPointerEnterCapture={undefined}
                    onPointerLeaveCapture={undefined}
                  >
                    <Builds
                      org={organization}
                      repo={repository}
                      setupTriggerUuid={setupBuildTriggerUuid}
                      repoDetails={repoDetails}
                    />
                  </Tab>
                  <Tab
                    eventKey={TabIndex.Settings}
                    title={<TabTitleText>Settings</TabTitleText>}
                    isHidden={!repoDetails?.can_admin}
                    onPointerEnterCapture={undefined}
                    onPointerLeaveCapture={undefined}
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
          </DrawerContentBody>
        </DrawerContent>
      </Drawer>
    </>
  );
}
