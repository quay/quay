import {renderHook, act, waitFor} from '@testing-library/react';
import React from 'react';
import {QueryClientProvider} from '@tanstack/react-query';
import {createTestQueryClient} from 'src/test-utils';
import {useOrganizationSettings} from './UseOrganizationSettings';
import {updateOrgSettings} from 'src/resources/OrganizationResource';

vi.mock('src/resources/OrganizationResource', () => ({
  updateOrgSettings: vi.fn(),
}));

/** QueryClientProvider wrapper for hooks that use React Query. */
function wrapper({children}: {children: React.ReactNode}) {
  const [queryClient] = React.useState(() => createTestQueryClient());
  return React.createElement(
    QueryClientProvider,
    {client: queryClient},
    children,
  );
}

describe('useOrganizationSettings', () => {
  beforeEach(() => {
    localStorage.clear();
    vi.clearAllMocks();
  });

  it('calls updateOrgSettings and fires onSuccess', async () => {
    vi.mocked(updateOrgSettings).mockResolvedValueOnce({} as any);
    const onSuccess = vi.fn();
    const onError = vi.fn();
    const {result} = renderHook(
      () => useOrganizationSettings({name: 'myorg', onSuccess, onError}),
      {wrapper},
    );
    act(() => {
      result.current.updateOrgSettings({email: 'new@example.com'});
    });
    await waitFor(() => expect(onSuccess).toHaveBeenCalled());
    expect(updateOrgSettings).toHaveBeenCalledWith('myorg', {
      email: 'new@example.com',
    });
  });

  it('fires onError on failure', async () => {
    const err = new Error('Settings update failed');
    vi.mocked(updateOrgSettings).mockRejectedValueOnce(err);
    const onSuccess = vi.fn();
    const onError = vi.fn();
    const {result} = renderHook(
      () => useOrganizationSettings({name: 'myorg', onSuccess, onError}),
      {wrapper},
    );
    act(() => {
      result.current.updateOrgSettings({email: 'bad@example.com'});
    });
    await waitFor(() => expect(onError).toHaveBeenCalledWith(err));
    expect(onSuccess).not.toHaveBeenCalled();
  });
});
