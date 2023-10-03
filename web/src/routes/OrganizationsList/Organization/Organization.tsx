import {
  Drawer,
  DrawerContent,
  DrawerContentBody,
  Page,
  PageSection,
  PageSectionVariants,
  Tab,
  Tabs,
  TabTitleText,
  Title,
} from '@patternfly/react-core';
import {useParams, useSearchParams} from 'react-router-dom';
import {useCallback, useRef, useState} from 'react';
import RepositoriesList from 'src/routes/RepositoriesList/RepositoriesList';
import Settings from './Tabs/Settings/Settings';
import {QuayBreadcrumb} from 'src/components/breadcrumb/Breadcrumb';
import {useOrganization} from 'src/hooks/UseOrganization';
import {useOrganizations} from 'src/hooks/UseOrganizations';
import RobotAccountsList from 'src/routes/RepositoriesList/RobotAccountsList';
import {useQuayConfig} from 'src/hooks/UseQuayConfig';
import TeamsAndMembershipList from './Tabs/TeamsAndMembership/TeamsAndMembershipList';
import ManageMembersList from './Tabs/TeamsAndMembership/TeamsView/ManageMembers/ManageMembersList';
import CreatePermissionDrawer from './Tabs/DefaultPermissions/createPermissionDrawer/CreatePermissionDrawer';
import DefaultPermissionsList from './Tabs/DefaultPermissions/DefaultPermissionsList';

export enum DrawerContentType {
  None,
  CreatePermissionSpecificUser,
}

export default function Organization() {
  const quayConfig = useQuayConfig();
  const {organizationName, teamName} = useParams();
  const {usernames} = useOrganizations();
  const isUserOrganization = usernames.includes(organizationName);

  const [searchParams, setSearchParams] = useSearchParams();

  const {organization} = useOrganization(organizationName);

  const [activeTabKey, setActiveTabKey] = useState<string>(
    searchParams.get('tab') || 'Repositories',
  );

  const onTabSelect = useCallback(
    (_event: React.MouseEvent<HTMLElement, MouseEvent>, tabKey: string) => {
      tabKey = tabKey.replace(/ /g, '');
      setSearchParams({tab: tabKey});
      setActiveTabKey(tabKey);
    },
    [],
  );

  const fetchTabVisibility = (tabname) => {
    if (quayConfig?.config?.REGISTRY_STATE == 'readonly') {
      return false;
    }

    if (!isUserOrganization && organization && tabname == 'Settings') {
      return organization.is_org_admin || organization.is_admin;
    }
    return false;
  };

  const [drawerContent, setDrawerContent] = useState<DrawerContentType>(
    DrawerContentType.None,
  );

  const closeDrawer = () => {
    setDrawerContent(DrawerContentType.None);
  };

  const drawerRef = useRef<HTMLDivElement>();

  const drawerContentOptions = {
    [DrawerContentType.None]: null,
    [DrawerContentType.CreatePermissionSpecificUser]: (
      <CreatePermissionDrawer
        orgName={organizationName}
        closeDrawer={closeDrawer}
        drawerRef={drawerRef}
        drawerContent={drawerContent}
      />
    ),
  };

  const repositoriesSubNav = [
    {
      name: 'Repositories',
      component: <RepositoriesList organizationName={organizationName} />,
      visible: true,
    },
    {
      name: 'Teams and membership',
      component: !teamName ? (
        <TeamsAndMembershipList
          key={window.location.pathname}
          organizationName={organizationName}
        />
      ) : (
        <ManageMembersList />
      ),
      visible:
        !isUserOrganization &&
        organization?.is_member &&
        organization?.is_admin,
    },
    {
      name: 'Robot accounts',
      component: (
        <RobotAccountsList
          organizationName={organizationName}
          isUser={isUserOrganization}
        />
      ),
      visible: true,
    },
    {
      name: 'Default permissions',
      component: (
        <DefaultPermissionsList
          orgName={organizationName}
          setDrawerContent={setDrawerContent}
        />
      ),
      visible: !isUserOrganization && organization?.is_admin,
    },
    {
      name: 'Settings',
      component: (
        <Settings
          organizationName={organizationName}
          isUserOrganization={isUserOrganization}
        />
      ),
      visible: fetchTabVisibility('Settings'),
    },
  ];

  return (
    <Drawer
      isExpanded={drawerContent != DrawerContentType.None}
      onExpand={() => {
        drawerRef.current && drawerRef.current.focus();
      }}
    >
      <DrawerContent panelContent={drawerContentOptions[drawerContent]}>
        <DrawerContentBody>
          <Page>
            <QuayBreadcrumb />
            <PageSection
              variant={PageSectionVariants.light}
              className="no-padding-bottom"
            >
              <Title data-testid="repo-title" headingLevel="h1">
                {organizationName}
              </Title>
            </PageSection>
            <PageSection
              variant={PageSectionVariants.light}
              padding={{default: 'noPadding'}}
            >
              <Tabs activeKey={activeTabKey} onSelect={onTabSelect}>
                {repositoriesSubNav
                  .filter((nav) => nav.visible)
                  .map((nav) => (
                    <Tab
                      key={nav.name}
                      eventKey={nav.name.replace(/ /g, '')}
                      title={<TabTitleText>{nav.name}</TabTitleText>}
                    >
                      {nav.component}
                    </Tab>
                  ))}
              </Tabs>
            </PageSection>
          </Page>
        </DrawerContentBody>
      </DrawerContent>
    </Drawer>
  );
}
