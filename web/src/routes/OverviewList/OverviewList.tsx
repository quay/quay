import {
  Button,
  Title,
  Tabs,
  Tab,
  TabTitleText,
  Text,
  Panel,
  Brand,
  Divider,
  PanelMainBody,
  Flex,
  FlexItem,
} from '@patternfly/react-core';
import GettingStarted from './GettingStarted';
import KeyFeatures from './KeyFeatures';
import RecommendedContent from './RecommendedContent';
import Pricing from './Pricing/Pricing';
import React from 'react';
import './css/OverviewList.scss';
import {ExternalLinkAltIcon} from '@patternfly/react-icons';
import logo from 'src/assets/Technology_icon-Red_Hat-Quay-Standard-RGB.svg';

export default function OverviewList() {
  const handleTabClick = (
    event: React.MouseEvent<any> | React.KeyboardEvent | MouseEvent,
    tabIndex: string | number,
  ) => {
    setActiveTabKey(tabIndex);
  };

  const [activeTabKey, setActiveTabKey] = React.useState<string | number>(0);

  const OverviewHeader = (
    <Panel style={{maxHeight: '144px'}}>
      <PanelMainBody>
        <Flex display={{default: 'inlineFlex'}}>
          <FlexItem className="overview-logo">
            <Brand
              className="overview-logo"
              src={logo}
              alt="Fallback quay logo"
            />
          </FlexItem>
          <Divider
            orientation={{default: 'vertical'}}
            style={{maxHeight: '96px'}}
          />
          <FlexItem className="overview-info">
            <Title headingLevel="h1">Red Hat Quay.io</Title>
            <Text>
              Secure, Scalable, and Flexible: Quay.io Image Registry for Cloud
              Native Applications
            </Text>
            <Button variant="link" style={{paddingLeft: '0'}}>
              Learn More <ExternalLinkAltIcon />
            </Button>
          </FlexItem>
        </Flex>
      </PanelMainBody>
    </Panel>
  );

  return (
    <div className="overview-list">
      {OverviewHeader}
      <Tabs
        className="overview-tabs"
        activeKey={activeTabKey}
        onSelect={handleTabClick}
        id="overview-tab"
      >
        <Tab eventKey={0} title={<TabTitleText>Overview</TabTitleText>}>
          <GettingStarted onPaidPlansClick={() => setActiveTabKey(1)} />

          <Title headingLevel="h1" className="overview-title">
            Key Features
          </Title>
          <KeyFeatures />

          <Title headingLevel="h1" className="overview-title">
            Recommended content
          </Title>
          <RecommendedContent />
        </Tab>

        <Tab
          eventKey={1}
          title={<TabTitleText>Pricing and Features</TabTitleText>}
          id="pricing-tab"
        >
          <Pricing />
        </Tab>

        <Tab
          eventKey={2}
          title={
            <a
              href="https://cloud.redhat.com/blog/tag/quay-io"
              style={{color: '#6a6e73', textDecoration: 'none'}}
            >
              <TabTitleText>Blog</TabTitleText>
              <ExternalLinkAltIcon />
            </a>
          }
          id="blog-tab"
        />
      </Tabs>
    </div>
  );
}
