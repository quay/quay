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
import SettingsTab from './ManageOAuthApplicationTabs/SettingsTab';
import OAuthInformationTab from './ManageOAuthApplicationTabs/OAuthInformationTab';
import GenerateTokenTab from './ManageOAuthApplicationTabs/GenerateTokenTab';

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
    <Drawer isExpanded={props.isDrawerOpen} data-testid="manage-oauth-drawer">
      <DrawerContent
        panelContent={
          <DrawerPanelContent widths={{default: 'width_50'}}>
            <DrawerHead>
              <Title headingLevel="h4" size="md">
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
                  data-testid="settings-tab"
                >
                  <SettingsTab
                    application={props.application}
                    orgName={props.orgName}
                    onSuccess={() => {
                      // Could refresh data or close drawer on success
                    }}
                  />
                </Tab>
                <Tab
                  eventKey="oauth-info"
                  title={<TabTitleText>OAuth Information</TabTitleText>}
                  aria-label="OAuth Information Tab"
                  data-testid="oauth-information-tab"
                >
                  <OAuthInformationTab
                    application={props.application}
                    orgName={props.orgName}
                    onSuccess={() => {
                      // Could refresh data or close drawer on success
                    }}
                    updateSelectedApplication={props.updateSelectedApplication}
                  />
                </Tab>
                <Tab
                  eventKey="generate-token"
                  title={<TabTitleText>Generate Token</TabTitleText>}
                  aria-label="Generate Token Tab"
                  data-testid="generate-token-tab"
                >
                  <GenerateTokenTab
                    application={props.application}
                    orgName={props.orgName}
                  />
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
  updateSelectedApplication: (updatedApplication: IOAuthApplication) => void;
}
