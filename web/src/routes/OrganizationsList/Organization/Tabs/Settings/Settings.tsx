import React from 'react';
import {useSearchParams} from 'react-router-dom';
import {
  Tabs,
  Tab,
  TabContent,
  TabTitleText,
  Flex,
  FlexItem,
} from '@patternfly/react-core';
import {useOrganization} from 'src/hooks/UseOrganization';
import {useQuayConfig} from 'src/hooks/UseQuayConfig';
import {useOrgMirrorExists} from 'src/hooks/UseOrgMirrorExists';
import {useFetchProxyCacheConfig} from 'src/hooks/UseProxyCache';
import {useNamespaceImmutabilityPolicies} from 'src/hooks/UseNamespaceImmutabilityPolicies';
import AutoPruning from './AutoPruning';
import {BillingInformation} from './BillingInformation';
import {CliConfiguration} from './CLIConfiguration';
import {GeneralSettings} from './GeneralSettings';
import ImmutabilityPolicies from './ImmutabilityPolicies';
import NamespaceNotifications from './NamespaceNotifications';
import {OrgMirroringState} from './OrgMirroringState';
import {ProxyCacheConfig} from './ProxyCacheConfig';
import {QuotaManagement} from './QuotaManagement';

export default function Settings(props: SettingsProps) {
  const organizationName = location.pathname.split('/')[2];
  const {isUserOrganization} = useOrganization(organizationName);

  const [searchParams, setSearchParams] = useSearchParams();
  const activeTabId = searchParams.get('settingsTab') || 'generalsettings';
  const quayConfig = useQuayConfig();

  const {isOrgMirrored, isLoading: isOrgMirrorLoading} = useOrgMirrorExists(
    props.organizationName,
    !!quayConfig?.features?.ORG_MIRROR && !props.isUserOrganization,
  );
  const {
    isProxyCacheConfigured,
    isLoadingProxyCacheConfig: isProxyCacheLoading,
  } = useFetchProxyCacheConfig(
    props.organizationName,
    !!quayConfig?.features?.PROXY_CACHE && !props.isUserOrganization,
  );
  const {
    nsPolicies,
    isLoading: isImmutabilityLoading,
    isError: isImmutabilityError,
  } = useNamespaceImmutabilityPolicies(
    props.organizationName,
    !!quayConfig?.features?.IMMUTABLE_TAGS,
  );
  const hasImmutabilityPolicies =
    !isImmutabilityError && (nsPolicies?.length ?? 0) > 0;
  const immutabilityResolved =
    !quayConfig?.features?.IMMUTABLE_TAGS ||
    (!isImmutabilityLoading && !isImmutabilityError);
  const proxyCacheResolved =
    !quayConfig?.features?.PROXY_CACHE ||
    props.isUserOrganization ||
    !isProxyCacheLoading;
  const orgMirrorResolved =
    !quayConfig?.features?.ORG_MIRROR ||
    props.isUserOrganization ||
    !isOrgMirrorLoading;
  const mutualExclusionLoaded =
    orgMirrorResolved && proxyCacheResolved && immutabilityResolved;

  const handleTabClick = (event: React.MouseEvent, tabId: string | number) => {
    setSearchParams((params) => {
      const next = new URLSearchParams(params);
      next.set('tab', 'Settings');
      next.set('settingsTab', String(tabId));
      return next;
    });
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
      name: 'Plan information',
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
      visible:
        quayConfig?.features?.AUTO_PRUNE &&
        mutualExclusionLoaded &&
        !isOrgMirrored,
    },
    {
      name: 'Immutability Policies',
      id: 'immutabilitypolicies',
      content: () => <ImmutabilityPolicies org={props.organizationName} />,
      visible:
        quayConfig?.features?.IMMUTABLE_TAGS &&
        mutualExclusionLoaded &&
        !isOrgMirrored &&
        !isProxyCacheConfigured,
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
        mutualExclusionLoaded &&
        !isOrgMirrored &&
        !hasImmutabilityPolicies,
    },
    {
      name: 'Organization state',
      id: 'organizationstate',
      content: () => (
        <OrgMirroringState organizationName={props.organizationName} />
      ),
      visible:
        quayConfig?.features?.ORG_MIRROR &&
        !props.isUserOrganization &&
        mutualExclusionLoaded &&
        !isProxyCacheConfigured &&
        !hasImmutabilityPolicies,
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
    {
      name: 'Notifications',
      id: 'namespacenotifications',
      content: () => (
        <NamespaceNotifications
          organizationName={props.organizationName}
          isUser={props.isUserOrganization}
        />
      ),
      visible: !!quayConfig?.features?.QUOTA_NOTIFICATIONS,
    },
  ];

  const visibleTabs = tabs.filter((tab) => tab.visible === true);
  const normalizedActiveId = visibleTabs.some((tab) => tab.id === activeTabId)
    ? activeTabId
    : (visibleTabs[0]?.id ?? null);
  const activeTab = normalizedActiveId
    ? visibleTabs.find((tab) => tab.id === normalizedActiveId)
    : null;

  if (visibleTabs.length === 0) {
    return null;
  }

  return (
    <Flex
      flexWrap={{default: 'nowrap'}}
      direction={{default: 'column', md: 'row'}}
    >
      <FlexItem>
        <Tabs
          activeKey={normalizedActiveId}
          onSelect={handleTabClick}
          isVertical
          aria-label="Settings sections"
          role="region"
        >
          {visibleTabs.map((tab) => (
            <Tab
              key={tab.id}
              eventKey={tab.id}
              tabContentId={`settings-panel-${tab.id}`}
              data-testid={tab.name}
              title={
                <TabTitleText
                  className="pf-v6-u-text-nowrap"
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
        alignSelf={{default: 'alignSelfStretch', md: 'alignSelfCenter'}}
        style={{padding: '20px'}}
      >
        {activeTab && (
          <TabContent
            id={`settings-panel-${activeTab.id}`}
            eventKey={activeTab.id}
            activeKey={normalizedActiveId}
            aria-labelledby={`pf-tab-${activeTab.id}`}
          >
            {activeTab.content()}
          </TabContent>
        )}
      </FlexItem>
    </Flex>
  );
}

type SettingsProps = {
  organizationName: string;
  isUserOrganization: boolean;
};
