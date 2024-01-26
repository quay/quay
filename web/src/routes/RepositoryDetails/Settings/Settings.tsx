import {Flex, FlexItem, Tab, Tabs, TabTitleText} from '@patternfly/react-core';
import {useState} from 'react';
import {DrawerContentType} from 'src/routes/RepositoryDetails/Types';
import DeleteRepository from './DeleteRepository';
import Permissions from './Permissions';
import Notifications from './Notifications';
import Visibility from './Visibility';
import {RepositoryStateForm} from './RepositoryState';
import {RepositoryDetails} from 'src/resources/RepositoryResource';
import {useQuayConfig} from 'src/hooks/UseQuayConfig';
import Policies from './Policies';

export default function Settings(props: SettingsProps) {
  const [activeTabIndex, setActiveTabIndex] = useState(0);
  const config = useQuayConfig();
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
      name: 'Policies',
      id: 'policies',
      content: <Policies org={props.org} repo={props.repo} />,
    },
    {
      name: <div style={{color: 'red'}}>Delete Repository</div>,
      id: 'deleterepository',
      content: <DeleteRepository org={props.org} repo={props.repo} />,
    },
  ];

  return (
    <Flex flexWrap={{default: 'nowrap'}}>
      <FlexItem>
        <Tabs
          activeKey={activeTabIndex}
          onSelect={(e, index: number) => setActiveTabIndex(index)}
          isVertical
          aria-label="Repository Settings Tabs"
          role="region"
        >
          {tabs.map((tab, tabIndex) => (
            <Tab
              key={tab.id}
              eventKey={tabIndex}
              title={<TabTitleText>{tab.name}</TabTitleText>}
            />
          ))}
        </Tabs>
      </FlexItem>
      <FlexItem
        alignSelf={{default: 'alignSelfCenter'}}
        style={{padding: '20px', width: '100%'}}
      >
        {tabs.at(activeTabIndex).content}
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
