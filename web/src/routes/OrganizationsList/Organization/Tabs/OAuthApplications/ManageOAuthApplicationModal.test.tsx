import React from 'react';
import {render, screen, userEvent, waitFor} from 'src/test-utils';
import ManageOAuthApplicationModal from './ManageOAuthApplicationModal';

const componentMocks = vi.hoisted(() => ({
  settingsTab: vi.fn(() => null),
  oauthInformationTab: vi.fn(() => null),
  apiAccessTokensTab: vi.fn(() => null),
}));

vi.mock('./ManageOAuthApplicationTabs/SettingsTab', () => ({
  default: componentMocks.settingsTab,
}));

vi.mock('./ManageOAuthApplicationTabs/OAuthInformationTab', () => ({
  default: componentMocks.oauthInformationTab,
}));

vi.mock('./ManageOAuthApplicationTabs/APIAccessTokensTab', () => ({
  default: componentMocks.apiAccessTokensTab,
}));

const application = {
  application_uri: 'https://example.com',
  avatar_email: '',
  client_id: 'client1',
  client_secret: 'secret',
  description: 'Test app',
  name: 'test-app',
  redirect_uri: 'https://example.com/callback',
};

describe('ManageOAuthApplicationModal', () => {
  beforeEach(() => {
    vi.resetAllMocks();
  });

  it('mounts API access tokens only after the tab is selected', async () => {
    const user = userEvent.setup();

    render(
      <ManageOAuthApplicationModal
        isModalOpen
        handleModalToggle={vi.fn()}
        application={application}
        orgName="myorg"
        updateSelectedApplication={vi.fn()}
      />,
    );

    expect(componentMocks.settingsTab).toHaveBeenCalled();
    expect(componentMocks.apiAccessTokensTab).not.toHaveBeenCalled();

    await user.click(screen.getByRole('tab', {name: 'API Access Tokens'}));

    await waitFor(() => {
      expect(componentMocks.apiAccessTokensTab).toHaveBeenCalled();
    });
  });
});
