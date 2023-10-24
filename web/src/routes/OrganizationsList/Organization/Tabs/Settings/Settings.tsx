import {useState} from 'react';
import {Tabs, Tab, TabTitleText, Flex, FlexItem} from '@patternfly/react-core';
import {useOrganization} from 'src/hooks/UseOrganization';
import {useQuayConfig} from 'src/hooks/UseQuayConfig';
import AutoPruning from './AutoPruning';
import {BillingInformation} from './BillingInformation';
import {CliConfiguration} from './CLIConfiguration';
import {GeneralSettings} from './GeneralSettings';

export default function Settings(props: SettingsProps) {
  const organizationName = location.pathname.split('/')[2];
  const {isUserOrganization} = useOrganization(organizationName);

  const [activeTabIndex, setActiveTabIndex] = useState(0);
  const quayConfig = useQuayConfig();

  const handleTabClick = (event, tabIndex) => {
    setActiveTabIndex(tabIndex);
  };

  const tabs = [
    {
      name: 'General Settings',
      id: 'generalsettings',
      content: <GeneralSettings organizationName={props.organizationName} />,
      visible: true,
    },
    {
      name: 'Billing Information',
      id: 'billinginformation',
      content: <BillingInformation organizationName={props.organizationName} />,
      visible: quayConfig?.features?.BILLING,
    },
    {
      name: 'CLI Configuration',
      id: 'cliconfig',
      content: <CliConfiguration />,
      visible: isUserOrganization,
    },
    {
      name: 'Auto-Prune Policies',
      id: 'autoprunepolicies',
      content: (
        <AutoPruning
          org={props.organizationName}
          isUser={props.isUserOrganization}
        />
      ),
      visible: quayConfig?.features?.AUTO_PRUNE,
    },
  ];

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
          {tabs
            .filter((tab) => tab.visible === true)
            .map((tab, tabIndex) => (
              <Tab
                key={tab.id}
                id={tab.id}
                eventKey={tabIndex}
                title={<TabTitleText>{tab.name}</TabTitleText>}
              />
            ))}
        </Tabs>
      </FlexItem>

      <FlexItem
        alignSelf={{default: 'alignSelfCenter'}}
        className="pf-v5-u-p-lg"
      >
        {tabs.filter((tab) => tab.visible === true).at(activeTabIndex).content}
      </FlexItem>
    </Flex>
  );
}

type SettingsProps = {
  organizationName: string;
  isUserOrganization: boolean;
};
