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
import RobotAccountsList from 'src/routes/RepositoriesList/RobotAccountsList';

export default function Organization() {
  const location = useLocation();
  const {organizationName} = useParams();
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

  const repositoriesSubNav = [
    {
      name: 'Repositories',
      component: <RepositoriesList organizationName={organizationName} />,
      visible: true,
    },
    {
      name: 'Robot accounts',
      component: <RobotAccountsList organizationName={organizationName} />,
      visible: organization.is_org_admin || organization.is_admin,

    },
    {
      name: 'Settings',
      component: <Settings organizationName={organizationName} />,
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
          {organizationName}
        </Title>
      </PageSection>
      <PageSection
        variant={PageSectionVariants.light}
        padding={{default: 'noPadding'}}
      >
        <Tabs activeKey={activeTabKey} onSelect={onTabSelect}>
          {repositoriesSubNav.map((nav) => (
            <Tab
              key={nav.name}
              eventKey={nav.name}
              title={<TabTitleText>{nav.name}</TabTitleText>}
              isHidden={!nav.visible}
            >
              {nav.component}
            </Tab>
          ))}
        </Tabs>
      </PageSection>
    </Page>
  );
}
