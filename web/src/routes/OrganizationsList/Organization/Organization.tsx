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
import RobotAccountsList from 'src/routes/RepositoriesList/RobotAccountsList';
import {useQuayConfig} from 'src/hooks/UseQuayConfig';
import TeamsAndMembershipList from './Tabs/TeamsAndMembership/TeamsAndMembershipList';
import ManageMembersList from './Tabs/TeamsAndMembership/TeamsView/ManageMembers/ManageMembersList';
import CreatePermissionDrawer from './Tabs/DefaultPermissions/createPermissionDrawer/CreatePermissionDrawer';
import DefaultPermissionsList from './Tabs/DefaultPermissions/DefaultPermissionsList';
import AddNewTeamMemberDrawer from './Tabs/TeamsAndMembership/TeamsView/ManageMembers/AddNewTeamMemberDrawer';

export enum OrganizationDrawerContentType {
  None,
  AddNewTeamMemberDrawer,
  CreatePermissionSpecificUser,
}

export default function Organization() {
  const quayConfig = useQuayConfig();
  const {organizationName, teamName} = useParams();

  const [searchParams, setSearchParams] = useSearchParams();

  const {organization, isUserOrganization} = useOrganization(organizationName);

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

    if (isUserOrganization) {
      return true;
    }

    if (
      !isUserOrganization &&
      organization &&
      (tabname == 'Settings' || tabname == 'Robot accounts')
    ) {
      return organization.is_org_admin || organization.is_admin;
    }
    return false;
  };

  const [drawerContent, setDrawerContent] =
    useState<OrganizationDrawerContentType>(OrganizationDrawerContentType.None);

  const closeDrawer = () => {
    setDrawerContent(OrganizationDrawerContentType.None);
  };

  const drawerRef = useRef<HTMLDivElement>();

  const drawerContentOptions = {
    [OrganizationDrawerContentType.None]: null,
    [OrganizationDrawerContentType.CreatePermissionSpecificUser]: (
      <CreatePermissionDrawer
        orgName={organizationName}
        closeDrawer={closeDrawer}
        drawerRef={drawerRef}
        drawerContent={drawerContent}
      />
    ),
    [OrganizationDrawerContentType.AddNewTeamMemberDrawer]: (
      <AddNewTeamMemberDrawer
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
        <TeamsAndMembershipList key={window.location.pathname} />
      ) : (
        <ManageMembersList setDrawerContent={setDrawerContent} />
      ),
      visible: organization?.is_member,
    },
    {
      name: 'Robot accounts',
      component: (
        <RobotAccountsList
          organizationName={organizationName}
          isUser={isUserOrganization}
        />
      ),
      visible: fetchTabVisibility('Robot accounts'),
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
      isExpanded={drawerContent != OrganizationDrawerContentType.None}
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
