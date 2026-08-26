import React from 'react';
import {render, screen} from 'src/test-utils';
import APIAccessTokensTab from './APIAccessTokensTab';
import {useCurrentUser} from 'src/hooks/UseCurrentUser';
import {useQuayConfig} from 'src/hooks/UseQuayConfig';
import type {IOAuthApplication} from 'src/resources/OAuthApplicationTypes';

const resourceMocks = vi.hoisted(() => ({
  fetchOAuthApplicationTokens: vi.fn(),
}));

vi.mock('src/resources/OAuthApplicationResource', async (importOriginal) => {
  const actual =
    await importOriginal<
      typeof import('src/resources/OAuthApplicationResource')
    >();
  return {
    ...actual,
    fetchOAuthApplicationTokens: resourceMocks.fetchOAuthApplicationTokens,
  };
});

vi.mock('src/hooks/UseCurrentUser', () => ({
  useCurrentUser: vi.fn(),
}));

vi.mock('src/hooks/UseQuayConfig', () => ({
  useQuayConfig: vi.fn(),
}));

const application: IOAuthApplication = {
  application_uri: 'https://example.com',
  avatar_email: '',
  client_id: 'client1',
  client_secret: 'secret',
  description: 'Test app',
  name: 'test-app',
  redirect_uri: 'https://example.com/callback',
};

describe('APIAccessTokensTab Suspense behavior', () => {
  beforeEach(() => {
    vi.resetAllMocks();
    vi.mocked(useCurrentUser).mockReturnValue({
      user: undefined,
      loading: false,
      error: null,
      isSuperUser: false,
    });
    vi.mocked(useQuayConfig).mockReturnValue(undefined);
  });

  it('renders the suspense fallback while the real token query is pending', () => {
    resourceMocks.fetchOAuthApplicationTokens.mockReturnValue(
      new Promise<never>(() => undefined),
    );

    render(<APIAccessTokensTab application={application} orgName="myorg" />);

    expect(screen.getByRole('heading', {name: 'Loading'})).toBeVisible();
    expect(resourceMocks.fetchOAuthApplicationTokens).toHaveBeenCalledWith(
      'myorg',
      'client1',
    );
  });

  it('renders the error boundary for an uncached query failure', async () => {
    vi.spyOn(console, 'error').mockImplementation(() => undefined);
    resourceMocks.fetchOAuthApplicationTokens.mockRejectedValue(
      new Error('Initial load failed'),
    );

    render(<APIAccessTokensTab application={application} orgName="myorg" />);

    expect(
      await screen.findByText('Unable to load API access tokens'),
    ).toBeVisible();
  });
});
