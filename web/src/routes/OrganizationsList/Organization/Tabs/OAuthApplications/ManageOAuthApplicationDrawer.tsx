import * as React from 'react';
import {useState} from 'react';
import {
  Drawer,
  DrawerContent,
  DrawerContentBody,
  DrawerPanelContent,
  DrawerHead,
  DrawerActions,
  DrawerCloseButton,
  Tabs,
  Tab,
  TabTitleText,
  Title,
} from '@patternfly/react-core';
import {IOAuthApplication} from 'src/hooks/UseOAuthApplications';

export default function ManageOAuthApplicationDrawer(
  props: ManageOAuthApplicationDrawerProps,
) {
  const [activeTabKey, setActiveTabKey] = useState<string>('settings');

  const handleTabClick = (
    event: React.MouseEvent<HTMLElement> | React.KeyboardEvent | MouseEvent,
    tabIndex: string,
  ) => {
    setActiveTabKey(tabIndex);
  };

  return (
    <Drawer isExpanded={props.isDrawerOpen}>
      <DrawerContent
        panelContent={
          <DrawerPanelContent widths={{default: 'width_50'}}>
            <DrawerHead>
              <Title headingLevel="h2" size="xl">
                Manage OAuth Application: {props.application?.name}
              </Title>
              <DrawerActions>
                <DrawerCloseButton onClick={props.handleDrawerToggle} />
              </DrawerActions>
            </DrawerHead>
            <DrawerContentBody>
              <Tabs
                activeKey={activeTabKey}
                onSelect={handleTabClick}
                aria-label="OAuth Application Management Tabs"
              >
                <Tab
                  eventKey="settings"
                  title={<TabTitleText>Settings</TabTitleText>}
                  aria-label="Settings Tab"
                >
                  <div style={{padding: '16px'}}>
                    <h3>Settings</h3>
                    <p>Settings tab content will go here...</p>
                    <p>Application: {props.application?.name}</p>
                    <p>Client ID: {props.application?.client_id}</p>
                  </div>
                </Tab>
                <Tab
                  eventKey="oauth-info"
                  title={<TabTitleText>OAuth Information</TabTitleText>}
                  aria-label="OAuth Information Tab"
                >
                  <div style={{padding: '16px'}}>
                    <h3>OAuth Information</h3>
                    <p>OAuth Information tab content will go here...</p>
                    <p>Client ID: {props.application?.client_id}</p>
                    <p>Client Secret: ****</p>
                  </div>
                </Tab>
                <Tab
                  eventKey="generate-token"
                  title={<TabTitleText>Generate Token</TabTitleText>}
                  aria-label="Generate Token Tab"
                >
                  <div style={{padding: '16px'}}>
                    <h3>Generate Token</h3>
                    <p>Generate Token tab content will go here...</p>
                    <p>Select scopes and generate access tokens</p>
                  </div>
                </Tab>
              </Tabs>
            </DrawerContentBody>
          </DrawerPanelContent>
        }
      >
        {props.children}
      </DrawerContent>
    </Drawer>
  );
}

interface ManageOAuthApplicationDrawerProps {
  isDrawerOpen: boolean;
  handleDrawerToggle: () => void;
  application: IOAuthApplication | null;
  orgName: string;
  children: React.ReactNode;
}
