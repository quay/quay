import {Flex, FlexItem, Tab, Tabs, TabTitleText} from '@patternfly/react-core';
import {useState} from 'react';
import {DrawerContentType} from 'src/routes/RepositoryDetails/Types';
import DeleteRepository from './DeleteRepository';
import Permissions from './Permissions';
import Notifications from './Notifications';
import Visibility from './Visibility';
import {RepositoryDetails} from 'src/resources/RepositoryResource';

export default function Settings(props: SettingsProps) {
  const [activeTabIndex, setActiveTabIndex] = useState(0);

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
      name: <div className="pf-v5-u-danger-color-100">Delete repository</div>,
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
        className="pf-v5-u-p-lg pf-v5-u-w-100"
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
