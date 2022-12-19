import {Tabs, Tab, TabTitleText} from '@patternfly/react-core';
import {useSearchParams, useNavigate} from 'react-router-dom';
import {useState} from 'react';
import Details from './Details/Details';
import SecurityReport from './SecurityReport/SecurityReport';
import {Tag} from 'src/resources/TagResource';
import {TabIndex} from './Types';
import {Packages} from './Packages/Packages';
import ErrorBoundary from 'src/components/errors/ErrorBoundary';
import {isErrorString} from 'src/resources/ErrorHandling';
import RequestError from 'src/components/errors/RequestError';

// Return the tab as an enum or null if it does not exist
function getTabIndex(tab: string) {
  if (Object.values(TabIndex).includes(tab as TabIndex)) {
    return tab as TabIndex;
  }
}

export default function TagTabs(props: TagTabsProps) {
  const [activeTabKey, setActiveTabKey] = useState<TabIndex>(TabIndex.Details);
  const navigate = useNavigate();

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
        <SecurityReport />
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
