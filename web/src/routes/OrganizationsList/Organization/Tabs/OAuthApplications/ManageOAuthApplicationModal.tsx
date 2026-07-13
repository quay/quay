import * as React from 'react';
import {useState} from 'react';
import {
  Modal,
  ModalBody,
  ModalHeader,
  ModalVariant,
  Tab,
  Tabs,
  TabTitleText,
} from '@patternfly/react-core';
import type {IOAuthApplication} from 'src/resources/OAuthApplicationTypes';
import SettingsTab from './ManageOAuthApplicationTabs/SettingsTab';
import OAuthInformationTab from './ManageOAuthApplicationTabs/OAuthInformationTab';
import APIAccessTokensTab from './ManageOAuthApplicationTabs/APIAccessTokensTab';

const manageOAuthModalStyle: React.CSSProperties = {
  height: '48rem',
  maxHeight: 'calc(100vh - 4rem)',
};

const manageOAuthTabContentStyle: React.CSSProperties = {
  paddingTop: 'var(--pf-t--global--spacer--lg)',
};

const ManageOAuthApplicationModal: React.FC<
  ManageOAuthApplicationModalProps
> = (props): React.ReactElement => {
  const [activeTabKey, setActiveTabKey] = useState<string>('settings');

  const handleTabClick = (
    event: React.MouseEvent<HTMLElement> | React.KeyboardEvent | MouseEvent,
    tabIndex: string,
  ): void => {
    setActiveTabKey(tabIndex);
  };

  return (
    <Modal
      variant={ModalVariant.large}
      isOpen={props.isModalOpen}
      onClose={props.handleModalToggle}
      style={manageOAuthModalStyle}
      data-testid="manage-oauth-modal"
    >
      <ModalHeader
        title={`Manage OAuth Application: ${props.application?.name || ''}`}
      />
      <ModalBody>
        <Tabs
          activeKey={activeTabKey}
          onSelect={handleTabClick}
          mountOnEnter
          aria-label="OAuth Application Management Tabs"
        >
          <Tab
            eventKey="settings"
            title={<TabTitleText>Settings</TabTitleText>}
            data-testid="settings-tab"
          >
            <div
              style={manageOAuthTabContentStyle}
              data-testid="settings-tab-content"
            >
              <SettingsTab
                application={props.application}
                orgName={props.orgName}
                onSuccess={() => {
                  // Could refresh data or close modal on success
                }}
              />
            </div>
          </Tab>
          <Tab
            eventKey="oauth-info"
            title={<TabTitleText>OAuth Information</TabTitleText>}
            data-testid="oauth-information-tab"
          >
            <div
              style={manageOAuthTabContentStyle}
              data-testid="oauth-information-tab-content"
            >
              <OAuthInformationTab
                application={props.application}
                orgName={props.orgName}
                onSuccess={() => {
                  // Could refresh data or close modal on success
                }}
                updateSelectedApplication={props.updateSelectedApplication}
              />
            </div>
          </Tab>
          <Tab
            eventKey="api-access-tokens"
            title={<TabTitleText>API Access Tokens</TabTitleText>}
            data-testid="api-access-tokens-tab"
          >
            <div
              style={manageOAuthTabContentStyle}
              data-testid="api-access-tokens-tab-content"
            >
              <APIAccessTokensTab
                application={props.application}
                orgName={props.orgName}
              />
            </div>
          </Tab>
        </Tabs>
      </ModalBody>
    </Modal>
  );
};

interface ManageOAuthApplicationModalProps {
  isModalOpen: boolean;
  handleModalToggle: () => void;
  application: IOAuthApplication | null;
  orgName: string;
  updateSelectedApplication: (updatedApplication: IOAuthApplication) => void;
}

export default ManageOAuthApplicationModal;
