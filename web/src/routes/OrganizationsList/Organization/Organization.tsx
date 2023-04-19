import {
  Page,
  PageSection,
  PageSectionVariants,
  Tab,
  Tabs,
  TabTitleText,
  Title,
} from '@patternfly/react-core';
import {useLocation, useSearchParams} from 'react-router-dom';
import {useCallback, useState} from 'react';
import RepositoriesList from 'src/routes/RepositoriesList/RepositoriesList';
import Settings from './Tabs/Settings/Settings';
import {QuayBreadcrumb} from 'src/components/breadcrumb/Breadcrumb';
import { useOrganization } from 'src/hooks/UseOrganization';
import RobotAccountsList from 'src/routes/RepositoriesList/RobotAccountsList';

export default function Organization() {
  const location = useLocation();
  const orgName = location.pathname.split('/')[2];
  const [searchParams, setSearchParams] = useSearchParams();

  const {organization} = useOrganization(orgName)

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

  const repositoriesSubNav = [
    {
      name: 'Repositories',
      component: <RepositoriesList />,
      visible: true
    },
    {
      name: 'Robot accounts',
      component: <RobotAccountsList orgName={orgName} />,
      visible: organization.is_org_admin || organization.is_admin,
    },
    {
      name: 'Settings',
      component: <Settings />,
      visible: organization.is_org_admin || organization.is_admin,
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
          {orgName}
        </Title>
      </PageSection>
      <PageSection
        variant={PageSectionVariants.light}
        padding={{default: 'noPadding'}}
      >
        <Tabs activeKey={activeTabKey} onSelect={onTabSelect}>
           {repositoriesSubNav.map((nav) => {
            nav.visible && (
              <Tab
                key={nav.name}
                eventKey={nav.name}
                title={<TabTitleText>{nav.name}</TabTitleText>}
              >
                {nav.component}
              </Tab>
            );
          })}
        </Tabs>
      </PageSection>
    </Page>
  );
}
