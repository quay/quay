import {Flex, FlexItem, Tab, Tabs, TabTitleText} from '@patternfly/react-core';
import {useEffect, useState} from 'react';
import {DrawerContentType} from 'src/routes/RepositoryDetails/Types';
import DeleteRepository from './DeleteRepository';
import Permissions from './Permissions';
import Notifications from './Notifications';
import Visibility from './Visibility';
import {RepositoryStateForm} from './RepositoryState';
import {RepositoryDetails} from 'src/resources/RepositoryResource';
import {useQuayConfig} from 'src/hooks/UseQuayConfig';
import RepositoryAutoPruning from 'src/routes/RepositoryDetails/Settings/RepositoryAutoPruning';
import RepositoryImmutabilityPolicies from 'src/routes/RepositoryDetails/Settings/RepositoryImmutabilityPolicies';
import {useOrganization} from 'src/hooks/UseOrganization';

export default function Settings(props: SettingsProps) {
  const [activeTabKey, setActiveTabKey] = useState('userandrobotpermissions');
  const config = useQuayConfig();
  const {isUserOrganization} = useOrganization(props.org);

  const tabs = [
    {
      name: 'User and robot permissions',
      id: 'userandrobotpermissions',
      content: (
        <Permissions
          org={props.org}
          repo={props.repo}
          setDrawerContent={props.setDrawerContent}
        />
      ),
    },
    ...(config?.features?.AUTO_PRUNE && props.repoDetails?.can_write
      ? [
          {
            name: 'Repository Auto-Prune Policies',
            id: 'repositoryautoprunepolicies',
            content: (
              <RepositoryAutoPruning
                organizationName={props.org}
                repoName={props.repo}
                isUser={isUserOrganization}
              />
            ),
          },
        ]
      : []),
    ...(config?.features?.IMMUTABLE_TAGS && props.repoDetails?.can_write
      ? [
          {
            name: 'Immutability Policies',
            id: 'repositoryimmutabilitypolicies',
            content: (
              <RepositoryImmutabilityPolicies
                organizationName={props.org}
                repoName={props.repo}
              />
            ),
          },
        ]
      : []),
    {
      name: 'Events and notifications',
      id: 'eventsandnotifications',
      content: (
        <Notifications
          org={props.org}
          repo={props.repo}
          setDrawerContent={props.setDrawerContent}
        />
      ),
    },
    ...(config?.features?.REPO_MIRROR
      ? [
          {
            name: 'Repository state',
            id: 'repositorystate',
            content: (
              <RepositoryStateForm
                org={props.org}
                repo={props.repo}
                repoDetails={props.repoDetails}
              />
            ),
          },
        ]
      : []),
    {
      name: 'Repository visibility',
      id: 'repositoryvisiblity',
      content: (
        <Visibility
          org={props.org}
          repo={props.repo}
          repoDetails={props.repoDetails}
        />
      ),
    },
    {
      name: <div style={{color: 'red'}}>Delete Repository</div>,
      id: 'deleterepository',
      content: <DeleteRepository org={props.org} repo={props.repo} />,
    },
  ];

  useEffect(() => {
    if (tabs.length > 0 && !tabs.some((tab) => tab.id === activeTabKey)) {
      setActiveTabKey(tabs[0].id);
    }
  }, [tabs, activeTabKey]);

  const activeTab = tabs.find((tab) => tab.id === activeTabKey) ?? tabs[0];

  return (
    <Flex flexWrap={{default: 'nowrap'}}>
      <FlexItem>
        <Tabs
          activeKey={activeTabKey}
          onSelect={(e, key: string | number) => setActiveTabKey(String(key))}
          isVertical
          aria-label="Repository Settings Tabs"
          role="region"
        >
          {tabs.map((tab) => (
            <Tab
              key={tab.id}
              eventKey={tab.id}
              title={<TabTitleText>{tab.name}</TabTitleText>}
              data-testid={`settings-tab-${tab.id}`}
            />
          ))}
        </Tabs>
      </FlexItem>
      <FlexItem
        alignSelf={{default: 'alignSelfFlexStart'}}
        style={{padding: '20px', width: '100%'}}
      >
        {activeTab?.content}
      </FlexItem>
    </Flex>
  );
}

interface SettingsProps {
  org: string;
  repo: string;
  repoDetails: RepositoryDetails;
  setDrawerContent: (content: DrawerContentType) => void;
}
