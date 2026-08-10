import {renderHook} from '@testing-library/react';
import {useQuayState} from './UseQuayState';

vi.mock('./UseQuayConfig', () => ({
  useQuayConfig: vi.fn(),
}));

import {useQuayConfig} from './UseQuayConfig';

describe('useQuayState', () => {
  beforeEach(() => {
    localStorage.clear();
    vi.clearAllMocks();
  });

  it('reports inReadOnlyMode=true when registry_state is readonly', () => {
    vi.mocked(useQuayConfig).mockReturnValue({
      registry_state: 'readonly',
      account_recovery_mode: false,
    } as any);
    const {result} = renderHook(() => useQuayState());
    expect(result.current.inReadOnlyMode).toBe(true);
    expect(result.current.inAccountRecoveryMode).toBe(false);
  });

  it('reports inReadOnlyMode=false when registry_state is normal', () => {
    vi.mocked(useQuayConfig).mockReturnValue({
      registry_state: 'normal',
      account_recovery_mode: false,
    } as any);
    const {result} = renderHook(() => useQuayState());
    expect(result.current.inReadOnlyMode).toBe(false);
  });

  it('reports inAccountRecoveryMode=true when flag is set', () => {
    vi.mocked(useQuayConfig).mockReturnValue({
      registry_state: 'normal',
      account_recovery_mode: true,
    } as any);
    const {result} = renderHook(() => useQuayState());
    expect(result.current.inAccountRecoveryMode).toBe(true);
  });

  it('returns false for both when config is undefined', () => {
    vi.mocked(useQuayConfig).mockReturnValue(undefined as any);
    const {result} = renderHook(() => useQuayState());
    expect(result.current.inReadOnlyMode).toBe(false);
    expect(result.current.inAccountRecoveryMode).toBe(false);
  });
});
