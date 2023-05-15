import {
  Page,
  PageSection,
  PageSectionVariants,
  Tab,
  Tabs,
  TabTitleText,
  Title,
} from '@patternfly/react-core';
import {useLocation, useParams, useSearchParams} from 'react-router-dom';
import {useCallback, useState} from 'react';
import RepositoriesList from 'src/routes/RepositoriesList/RepositoriesList';
import Settings from './Tabs/Settings/Settings';
import {QuayBreadcrumb} from 'src/components/breadcrumb/Breadcrumb';
import { useOrganization } from 'src/hooks/UseOrganization';
import {useOrganizations} from 'src/hooks/UseOrganizations';
import RobotAccountsList from 'src/routes/RepositoriesList/RobotAccountsList';
import {useQuayConfig} from 'src/hooks/UseQuayConfig';

export default function Organization() {
  const location = useLocation();
  const quayConfig = useQuayConfig();
  const {organizationName} = useParams();
  const {usernames} = useOrganizations();
  const isUserOrganization = usernames.includes(organizationName);

  const [searchParams, setSearchParams] = useSearchParams();

  const {organization} = useOrganization(organizationName);

  const [activeTabKey, setActiveTabKey] = useState<string>(
    searchParams.get('tab') || 'Repositories',
  );

  const onTabSelect = useCallback(
    (_event: React.MouseEvent<HTMLElement, MouseEvent>, tabKey: string) => {
      setSearchParams({tab: tabKey});
      setActiveTabKey(tabKey);
    },
    [],
  );

  const fetchTabVisibility = (tabname) => {
    if (quayConfig.config.REGISTRY_STATE == 'readonly') {
      return false;
    }

    if (!isUserOrganization && organization && tabname == 'Settings') {
      return organization.is_org_admin || organization.is_admin;
    }
    return true;
  }

  const repositoriesSubNav = [
    {
      name: 'Repositories',
      component: <RepositoriesList organizationName={organizationName} />,
      visible: true,
    },
    {
      name: 'Robot accounts',
      component: <RobotAccountsList organizationName={organizationName} />,
      visible: fetchTabVisibility('Robot accounts'),

    },
    {
      name: 'Settings',
      component: <Settings organizationName={organizationName} />,
      visible: fetchTabVisibility('Settings'),
    },
  ];

  return (
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
          {repositoriesSubNav.filter((nav) => nav.visible).map((nav)=> (
            <Tab
              key={nav.name}
              eventKey={nav.name}
              title={<TabTitleText>{nav.name}</TabTitleText>}
            >
              {nav.component}
            </Tab>
          ))}
        </Tabs>
      </PageSection>
    </Page>
  );
}
