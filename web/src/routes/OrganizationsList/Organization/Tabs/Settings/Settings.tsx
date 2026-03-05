import React, {useState} from 'react';
import {Tabs, Tab, TabTitleText, Flex, FlexItem} from '@patternfly/react-core';
import {useOrganization} from 'src/hooks/UseOrganization';
import {useQuayConfig} from 'src/hooks/UseQuayConfig';
import {useHasOrgMirrorConfig} from 'src/hooks/UseHasOrgMirrorConfig';
import {useHasProxyCacheConfig} from 'src/hooks/UseHasProxyCacheConfig';
import AutoPruning from './AutoPruning';
import {BillingInformation} from './BillingInformation';
import {CliConfiguration} from './CLIConfiguration';
import {GeneralSettings} from './GeneralSettings';
import ImmutabilityPolicies from './ImmutabilityPolicies';
import {OrgMirroringState} from './OrgMirroringState';
import {ProxyCacheConfig} from './ProxyCacheConfig';
import {QuotaManagement} from './QuotaManagement';

export default function Settings(props: SettingsProps) {
  const organizationName = location.pathname.split('/')[2];
  const {isUserOrganization} = useOrganization(organizationName);

  const [activeTabId, setActiveTabId] = useState<string>('generalsettings');
  const quayConfig = useQuayConfig();
  const {hasOrgMirrorConfig} = useHasOrgMirrorConfig(organizationName);
  const {hasProxyCacheConfig} = useHasProxyCacheConfig(organizationName);

  const handleTabClick = (
    event: React.MouseEvent,
    tabIndex: string | number,
  ) => {
    setActiveTabId(String(tabIndex));
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
      name: 'Immutability Policies',
      id: 'immutabilitypolicies',
      content: () => <ImmutabilityPolicies org={props.organizationName} />,
      visible:
        quayConfig?.features?.IMMUTABLE_TAGS &&
        !hasOrgMirrorConfig &&
        !hasProxyCacheConfig,
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
      visible:
        quayConfig?.features?.PROXY_CACHE &&
        !props.isUserOrganization &&
        !hasOrgMirrorConfig,
    },
    {
      name: 'Organization state',
      id: 'organizationstate',
      content: () => (
        <OrgMirroringState organizationName={props.organizationName} />
      ),
      visible: quayConfig?.features?.ORG_MIRROR && !props.isUserOrganization,
    },
    {
      name: 'Quota',
      id: 'quotamanagement',
      content: () => (
        <QuotaManagement
          organizationName={props.organizationName}
          isUser={props.isUserOrganization}
          view="organization-view"
        />
      ),
      visible:
        quayConfig?.features?.QUOTA_MANAGEMENT &&
        quayConfig?.features?.EDIT_QUOTA,
    },
  ];

  const visibleTabs = tabs.filter((tab) => tab.visible === true);
  const activeTab =
    visibleTabs.find((tab) => tab.id === activeTabId) ?? visibleTabs[0];

  return (
    <Flex flexWrap={{default: 'nowrap'}}>
      <FlexItem>
        <Tabs
          activeKey={activeTab?.id}
          onSelect={handleTabClick}
          isVertical
          aria-label="Tabs in the vertical example"
          role="region"
        >
          {visibleTabs.map((tab) => (
            <Tab
              key={tab.id}
              eventKey={tab.id}
              data-testid={tab.name}
              title={
                <TabTitleText
                  className="pf-v5-u-text-nowrap"
                  id={`pf-tab-${tab.id}`}
                >
                  {tab.name}
                </TabTitleText>
              }
            />
          ))}
        </Tabs>
      </FlexItem>

      <FlexItem
        alignSelf={{default: 'alignSelfCenter'}}
        style={{padding: '20px'}}
      >
        {activeTab?.content?.()}
      </FlexItem>
    </Flex>
  );
}

type SettingsProps = {
  organizationName: string;
  isUserOrganization: boolean;
};
