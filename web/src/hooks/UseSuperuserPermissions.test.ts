import {renderHook} from '@testing-library/react';
import {useSuperuserPermissions} from './UseSuperuserPermissions';

vi.mock('./UseCurrentUser', () => ({
  useCurrentUser: vi.fn(),
}));

vi.mock('./UseQuayState', () => ({
  useQuayState: vi.fn(),
}));

import {useCurrentUser} from './UseCurrentUser';
import {useQuayState} from './UseQuayState';

describe('useSuperuserPermissions', () => {
  beforeEach(() => {
    localStorage.clear();
    vi.clearAllMocks();
  });

  it('identifies regular superuser who can modify', () => {
    vi.mocked(useCurrentUser).mockReturnValue({
      user: {super_user: true, global_readonly_super_user: false} as any,
      loading: false,
      error: null,
      isSuperUser: true,
    });
    vi.mocked(useQuayState).mockReturnValue({
      inReadOnlyMode: false,
      inAccountRecoveryMode: false,
    });
    const {result} = renderHook(() => useSuperuserPermissions());
    expect(result.current.isSuperUser).toBe(true);
    expect(result.current.isReadOnlySuperUser).toBe(false);
    expect(result.current.canModify).toBe(true);
    expect(result.current.inReadOnlyMode).toBe(false);
  });

  it('identifies read-only superuser who cannot modify', () => {
    vi.mocked(useCurrentUser).mockReturnValue({
      user: {super_user: false, global_readonly_super_user: true} as any,
      loading: false,
      error: null,
      isSuperUser: true,
    });
    vi.mocked(useQuayState).mockReturnValue({
      inReadOnlyMode: false,
      inAccountRecoveryMode: false,
    });
    const {result} = renderHook(() => useSuperuserPermissions());
    expect(result.current.isSuperUser).toBe(true);
    expect(result.current.isReadOnlySuperUser).toBe(true);
    expect(result.current.canModify).toBe(false);
  });

  it('regular superuser cannot modify in read-only registry mode', () => {
    vi.mocked(useCurrentUser).mockReturnValue({
      user: {super_user: true, global_readonly_super_user: false} as any,
      loading: false,
      error: null,
      isSuperUser: true,
    });
    vi.mocked(useQuayState).mockReturnValue({
      inReadOnlyMode: true,
      inAccountRecoveryMode: false,
    });
    const {result} = renderHook(() => useSuperuserPermissions());
    expect(result.current.isSuperUser).toBe(true);
    expect(result.current.canModify).toBe(false);
    expect(result.current.inReadOnlyMode).toBe(true);
  });

  it('regular user is not a superuser', () => {
    vi.mocked(useCurrentUser).mockReturnValue({
      user: {super_user: false, global_readonly_super_user: false} as any,
      loading: false,
      error: null,
      isSuperUser: false,
    });
    vi.mocked(useQuayState).mockReturnValue({
      inReadOnlyMode: false,
      inAccountRecoveryMode: false,
    });
    const {result} = renderHook(() => useSuperuserPermissions());
    expect(result.current.isSuperUser).toBe(false);
    expect(result.current.canModify).toBe(false);
  });
});
