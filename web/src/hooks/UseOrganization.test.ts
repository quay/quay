import {renderHook, waitFor} from '@testing-library/react';
import React from 'react';
import {QueryClientProvider} from '@tanstack/react-query';
import {createTestQueryClient} from 'src/test-utils';
import {useOrganization} from './UseOrganization';
import {fetchOrg} from 'src/resources/OrganizationResource';

vi.mock('src/resources/OrganizationResource', () => ({
  fetchOrg: vi.fn(),
}));

vi.mock('./UseOrganizations', () => ({
  useOrganizations: vi.fn(() => ({usernames: ['testuser']})),
}));

function wrapper({children}: {children: React.ReactNode}) {
  const [queryClient] = React.useState(() => createTestQueryClient());
  return React.createElement(
    QueryClientProvider,
    {client: queryClient},
    children,
  );
}

describe('UseOrganization', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('identifies user organizations from the usernames list', async () => {
    const {result} = renderHook(() => useOrganization('testuser'), {wrapper});
    expect(result.current.isUserOrganization).toBe(true);
    expect(fetchOrg).not.toHaveBeenCalled();
  });

  it('fetches org data for non-user organizations', async () => {
    vi.mocked(fetchOrg).mockResolvedValueOnce({
      name: 'myorg',
      email: 'org@example.com',
    } as any);
    const {result} = renderHook(() => useOrganization('myorg'), {wrapper});
    await waitFor(() => expect(result.current.organization).toBeDefined());
    expect(result.current.isUserOrganization).toBe(false);
    expect(result.current.organization?.name).toBe('myorg');
    expect(fetchOrg).toHaveBeenCalledWith('myorg', expect.anything());
  });

  it('returns error when fetch fails', async () => {
    vi.mocked(fetchOrg).mockRejectedValueOnce(new Error('Not found'));
    const {result} = renderHook(() => useOrganization('badorg'), {wrapper});
    await waitFor(() => expect(result.current.error).toBeTruthy());
  });

  it('returns loading=true while fetching', () => {
    // eslint-disable-next-line @typescript-eslint/no-empty-function
    vi.mocked(fetchOrg).mockReturnValue(new Promise(() => {}));
    const {result} = renderHook(() => useOrganization('myorg'), {wrapper});
    expect(result.current.loading).toBe(true);
  });
});
