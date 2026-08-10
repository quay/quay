import {renderHook, act} from '@testing-library/react';
import {useEntities} from './UseEntities';
import {fetchEntities} from 'src/resources/UserResource';

vi.mock('src/resources/UserResource', () => ({
  fetchEntities: vi.fn(),
}));

describe('useEntities', () => {
  beforeEach(() => {
    localStorage.clear();
    vi.clearAllMocks();
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('starts with empty entities', () => {
    const {result} = renderHook(() => useEntities('myorg'));
    expect(result.current.entities).toEqual([]);
  });

  it('debounces search and fetches entities after 1 second', async () => {
    const mockEntities = [{name: 'alice', kind: 'user', is_robot: false}];
    vi.mocked(fetchEntities).mockResolvedValueOnce(mockEntities as any);
    const {result} = renderHook(() => useEntities('myorg'));
    act(() => {
      result.current.setSearchTerm('ali');
    });
    expect(fetchEntities).not.toHaveBeenCalled();
    // Advance fake timers past the 1s debounce and flush resulting async work
    await act(async () => {
      vi.advanceTimersByTime(1100);
    });
    expect(fetchEntities).toHaveBeenCalled();
    expect(result.current.entities).toHaveLength(1);
    expect(result.current.entities[0].name).toBe('alice');
  });

  it('sets isError on fetch failure', async () => {
    vi.mocked(fetchEntities).mockRejectedValueOnce(new Error('fail'));
    const {result} = renderHook(() => useEntities('myorg'));
    act(() => {
      result.current.setSearchTerm('bad');
    });
    await act(async () => {
      vi.advanceTimersByTime(1100);
    });
    expect(result.current.isError).toBe(true);
    expect(result.current.entities).toEqual([]);
  });
});
