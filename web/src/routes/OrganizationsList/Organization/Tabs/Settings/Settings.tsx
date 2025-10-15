import React, {useState} from 'react';
import {Tabs, Tab, TabTitleText, Flex, FlexItem} from '@patternfly/react-core';
import {useOrganization} from 'src/hooks/UseOrganization';
import {useQuayConfig} from 'src/hooks/UseQuayConfig';
import AutoPruning from './AutoPruning';
import {BillingInformation} from './BillingInformation';
import {CliConfiguration} from './CLIConfiguration';
import {GeneralSettings} from './GeneralSettings';
import {ProxyCacheConfig} from './ProxyCacheConfig';
import {QuotaManagement} from './QuotaManagement';

export default function Settings(props: SettingsProps) {
  const organizationName = location.pathname.split('/')[2];
  const {isUserOrganization} = useOrganization(organizationName);

  const [activeTabIndex, setActiveTabIndex] = useState(0);
  const quayConfig = useQuayConfig();

  const handleTabClick = (event: React.MouseEvent, tabIndex: number) => {
    setActiveTabIndex(tabIndex);
  };

  const tabs = [
    {
      name: 'General settings',
      id: 'generalsettings',
      content: () => (
        <GeneralSettings organizationName={props.organizationName} />
      ),
      visible: true,
    },
    {
      name: 'Billing information',
      id: 'billinginformation',
      content: () => (
        <BillingInformation organizationName={props.organizationName} />
      ),
      visible: quayConfig?.features?.BILLING,
    },
    {
      name: 'CLI configuration',
      id: 'cliconfig',
      content: () => <CliConfiguration />,
      visible: isUserOrganization,
    },
    {
      name: 'Auto-Prune Policies',
      id: 'autoprunepolicies',
      content: () => (
        <AutoPruning
          org={props.organizationName}
          isUser={props.isUserOrganization}
        />
      ),
      visible: quayConfig?.features?.AUTO_PRUNE,
    },
    {
      name: 'Proxy Cache',
      id: 'proxycacheconfig',
      content: () => (
        <ProxyCacheConfig
          organizationName={props.organizationName}
          isUser={props.isUserOrganization}
        />
      ),
      visible: quayConfig?.features?.PROXY_CACHE && !props.isUserOrganization,
    },
    {
      name: 'Quota',
      id: 'quotamanagement',
      content: () => (
        <QuotaManagement
          organizationName={props.organizationName}
          isUser={props.isUserOrganization}
        />
      ),
      visible:
        quayConfig?.features?.QUOTA_MANAGEMENT &&
        quayConfig?.features?.EDIT_QUOTA,
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
            ?.filter((tab) => tab.visible === true)
            ?.map((tab, tabIndex) => (
              <Tab
                key={tab.id}
                eventKey={tabIndex}
                data-testid={tab.name}
                title={
                  <TabTitleText
                    className="pf-v5-u-text-nowrap"
                    id={`pf-tab-${tabIndex}-${tab.id}`}
                  >
                    {tab.name}
                  </TabTitleText>
                }
              />
            )) || []}
        </Tabs>
      </FlexItem>

      <FlexItem
        alignSelf={{default: 'alignSelfCenter'}}
        style={{padding: '20px'}}
      >
        {tabs
          ?.filter((tab) => tab.visible === true)
          [activeTabIndex]?.content?.()}
      </FlexItem>
    </Flex>
  );
}

type SettingsProps = {
  organizationName: string;
  isUserOrganization: boolean;
};
