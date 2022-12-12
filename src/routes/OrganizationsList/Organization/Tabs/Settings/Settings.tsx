import {useState} from 'react';
import {Tabs, Tab, TabTitleText, Flex, FlexItem} from '@patternfly/react-core';
import {GeneralSettings} from './GeneralSettings';
import {BillingInformation} from './BillingInformation';
import {useLocation} from 'react-router-dom';
import {useOrganization} from 'src/hooks/UseOrganization';
import {CliConfiguration} from './CLIConfiguration';

export default function Settings() {
  const [activeTabIndex, setActiveTabIndex] = useState(0);
  const location = useLocation();
  const organizationName = location.pathname.split('/')[2];
  const {isUserOrganization} = useOrganization(organizationName);

  const handleTabClick = (event, tabIndex) => {
    setActiveTabIndex(tabIndex);
  };

  const tabs = [
    {
      name: 'General Settings',
      id: 'generalsettings',
      content: <GeneralSettings />,
    },
    {
      name: 'Billing Information',
      id: 'billinginformation',
      content: <BillingInformation />,
    },
  ];

  if (isUserOrganization) {
    tabs.push({
      name: 'CLI configuration',
      id: 'cliconfig',
      content: <CliConfiguration />,
    });
  }

  return (
    <Flex flexWrap={{default: 'nowrap'}}>
      <FlexItem>
        <Tabs
          activeKey={activeTabIndex}
          onSelect={handleTabClick}
          isVertical
          aria-label="Tabs in the vertical example"
          role="region"
        >
          {tabs.map((tab, tabIndex) => (
            <Tab
              key={tab.id}
              eventKey={tabIndex}
              title={<TabTitleText wrap="nowrap">{tab.name}</TabTitleText>}
            />
          ))}
        </Tabs>
      </FlexItem>

      <FlexItem
        alignSelf={{
          default: activeTabIndex != 2 ? 'alignSelfCenter' : 'alignSelfStretch',
        }}
        style={{padding: '20px'}}
      >
        {tabs.at(activeTabIndex).content}
      </FlexItem>
    </Flex>
  );
}
