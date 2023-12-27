import {Tab, TabTitleText, Tabs} from '@patternfly/react-core';
import {useState} from 'react';
import {useLocation, useNavigate, useSearchParams} from 'react-router-dom';
import {Tag} from 'src/resources/TagResource';
import Details from './Details/Details';
import {Packages} from './Packages/Packages';
import SecurityReport from './SecurityReport/SecurityReport';
import {TabIndex} from './Types';

// Return the tab as an enum or null if it does not exist
function getTabIndex(tab: string) {
  if (Object.values(TabIndex).includes(tab as TabIndex)) {
    return tab as TabIndex;
  }
}

export default function TagTabs(props: TagTabsProps) {
  const [activeTabKey, setActiveTabKey] = useState<TabIndex>(TabIndex.Details);
  const navigate = useNavigate();
  const location = useLocation();

  // Navigate to the correct tab
  const [searchParams] = useSearchParams();
  const requestedTabIndex = getTabIndex(searchParams.get('tab'));
  if (requestedTabIndex && requestedTabIndex !== activeTabKey) {
    setActiveTabKey(requestedTabIndex);
  }
  return (
    <Tabs
      activeKey={activeTabKey}
      onSelect={(e, tabIndex) => {
        navigate(`${location.pathname}?tab=${tabIndex}`);
      }}
      usePageInsets={true}
    >
      <Tab
        eventKey={TabIndex.Details}
        title={<TabTitleText>Details</TabTitleText>}
      >
        <Details
          org={props.org}
          repo={props.repo}
          tag={props.tag}
          digest={props.digest}
        />
      </Tab>
      <Tab
        eventKey={TabIndex.SecurityReport}
        title={<TabTitleText>Security Report</TabTitleText>}
      >
        <SecurityReport
          org={props.org}
          repo={props.repo}
          tag={props.tag}
          digest={props.digest}
        />
      </Tab>
      <Tab
        eventKey={TabIndex.Packages}
        title={<TabTitleText>Packages</TabTitleText>}
      >
        <Packages />
      </Tab>
    </Tabs>
  );
}

type TagTabsProps = {
  tag: Tag;
  org: string;
  repo: string;
  digest: string;
  err: string;
};
