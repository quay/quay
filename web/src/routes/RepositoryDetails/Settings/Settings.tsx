import {Flex, FlexItem, Tab, Tabs, TabTitleText} from '@patternfly/react-core';
import {useState} from 'react';
import {DrawerContentType} from 'src/routes/RepositoryDetails/Types';
import Permissions from './Permissions';

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
  setDrawerContent: (content: DrawerContentType) => void;
}
