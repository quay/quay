import {renderHook, act, waitFor} from '@testing-library/react';
import React from 'react';
import {QueryClientProvider} from '@tanstack/react-query';
import {createTestQueryClient} from 'src/test-utils';
import {useServiceKeys} from './UseServiceKeys';
import {
  fetchServiceKeys,
  createServiceKey,
  deleteServiceKey,
  approveServiceKey,
} from 'src/resources/ServiceKeysResource';

vi.mock('src/resources/ServiceKeysResource', () => ({
  fetchServiceKeys: vi.fn(),
  createServiceKey: vi.fn(),
  updateServiceKey: vi.fn(),
  deleteServiceKey: vi.fn(),
  approveServiceKey: vi.fn(),
}));

function wrapper({children}: {children: React.ReactNode}) {
  const [queryClient] = React.useState(() => createTestQueryClient());
  return React.createElement(
    QueryClientProvider,
    {client: queryClient},
    children,
  );
}

describe('useServiceKeys', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('fetches service keys and exposes them', async () => {
    const mockKeys = [
      {
        kid: 'kid1',
        name: 'Key 1',
        service: 'svc1',
        created_date: '2024-01-01',
        expiration_date: null,
      },
      {
        kid: 'kid2',
        name: 'Key 2',
        service: 'svc2',
        created_date: '2024-01-02',
        expiration_date: null,
      },
    ];
    vi.mocked(fetchServiceKeys).mockResolvedValueOnce(mockKeys as any);
    const {result} = renderHook(() => useServiceKeys(), {wrapper});
    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(result.current.serviceKeys).toEqual(mockKeys);
    expect(result.current.totalResults).toBe(2);
  });

  it('filters keys by search query', async () => {
    const mockKeys = [
      {
        kid: 'kid1',
        name: 'Alpha Key',
        service: 'svc1',
        created_date: '2024-01-01',
        expiration_date: null,
      },
      {
        kid: 'kid2',
        name: 'Beta Key',
        service: 'svc2',
        created_date: '2024-01-02',
        expiration_date: null,
      },
    ];
    vi.mocked(fetchServiceKeys).mockResolvedValueOnce(mockKeys as any);
    const {result} = renderHook(() => useServiceKeys(), {wrapper});
    await waitFor(() => expect(result.current.loading).toBe(false));
    act(() => {
      result.current.setSearch({query: 'alpha', field: 'name'});
    });
    expect(result.current.filteredKeys).toHaveLength(1);
    expect(result.current.filteredKeys[0].kid).toBe('kid1');
  });

  it('calls deleteServiceKey mutation', async () => {
    vi.mocked(fetchServiceKeys).mockResolvedValueOnce([]);
    vi.mocked(deleteServiceKey).mockResolvedValueOnce(undefined);
    const {result} = renderHook(() => useServiceKeys(), {wrapper});
    await waitFor(() => expect(result.current.loading).toBe(false));
    act(() => {
      result.current.deleteServiceKey('kid1');
    });
    await waitFor(() => expect(deleteServiceKey).toHaveBeenCalledWith('kid1'));
  });

  it('calls approveServiceKey mutation', async () => {
    vi.mocked(fetchServiceKeys).mockResolvedValueOnce([]);
    vi.mocked(approveServiceKey).mockResolvedValueOnce(undefined);
    const {result} = renderHook(() => useServiceKeys(), {wrapper});
    await waitFor(() => expect(result.current.loading).toBe(false));
    act(() => {
      result.current.approveServiceKey('kid2');
    });
    await waitFor(() => expect(approveServiceKey).toHaveBeenCalledWith('kid2'));
  });

  it('calls createServiceKey mutation', async () => {
    vi.mocked(fetchServiceKeys).mockResolvedValueOnce([]);
    vi.mocked(createServiceKey).mockResolvedValueOnce(undefined);
    const {result} = renderHook(() => useServiceKeys(), {wrapper});
    await waitFor(() => expect(result.current.loading).toBe(false));
    const keyData = {name: 'newkey', service: 'svc', expiration: 0, notes: ''};
    act(() => {
      result.current.createServiceKey(keyData as any);
    });
    await waitFor(() => expect(createServiceKey).toHaveBeenCalledWith(keyData));
  });
});
