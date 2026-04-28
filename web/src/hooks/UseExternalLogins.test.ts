import {renderHook, act, waitFor} from '@testing-library/react';
import {useExternalLogins} from './UseExternalLogins';

vi.mock('./UseQuayConfig', () => ({
  useQuayConfig: vi.fn(),
}));

import {useQuayConfig} from './UseQuayConfig';

describe('useExternalLogins', () => {
  beforeEach(() => {
    localStorage.clear();
    vi.clearAllMocks();
  });

  it('returns externalLogins from quay config', async () => {
    vi.mocked(useQuayConfig).mockReturnValue({
      external_login: [{id: 'github', title: 'GitHub', icon: 'github-icon'}],
      features: {DIRECT_LOGIN: true},
      config: {AUTHENTICATION_TYPE: 'Database'},
      registry_state: 'normal',
    } as any);
    const {result} = renderHook(() => useExternalLogins());
    await waitFor(() => expect(result.current.externalLogins).toHaveLength(1));
    expect(result.current.externalLogins[0].id).toBe('github');
  });

  it('hasExternalLogins returns false when no logins configured', () => {
    vi.mocked(useQuayConfig).mockReturnValue({
      external_login: [],
      features: {DIRECT_LOGIN: true},
      config: {},
      registry_state: 'normal',
    } as any);
    const {result} = renderHook(() => useExternalLogins());
    expect(result.current.hasExternalLogins()).toBe(false);
  });

  it('shouldShowDirectLogin returns true when DIRECT_LOGIN is enabled', () => {
    vi.mocked(useQuayConfig).mockReturnValue({
      external_login: [],
      features: {DIRECT_LOGIN: true},
      config: {AUTHENTICATION_TYPE: 'Database'},
      registry_state: 'normal',
    } as any);
    const {result} = renderHook(() => useExternalLogins());
    expect(result.current.shouldShowDirectLogin()).toBe(true);
  });

  it('shouldShowDirectLogin returns false for OIDC authentication', () => {
    vi.mocked(useQuayConfig).mockReturnValue({
      external_login: [{id: 'oidc', title: 'OIDC', icon: ''}],
      features: {DIRECT_LOGIN: true},
      config: {AUTHENTICATION_TYPE: 'OIDC'},
      registry_state: 'normal',
    } as any);
    const {result} = renderHook(() => useExternalLogins());
    expect(result.current.shouldShowDirectLogin()).toBe(false);
  });

  it('hasSingleSignin returns true for single provider without DIRECT_LOGIN', async () => {
    vi.mocked(useQuayConfig).mockReturnValue({
      external_login: [{id: 'github', title: 'GitHub', icon: ''}],
      features: {DIRECT_LOGIN: false},
      config: {},
      registry_state: 'normal',
    } as any);
    const {result} = renderHook(() => useExternalLogins());
    await waitFor(() => expect(result.current.externalLogins).toHaveLength(1));
    expect(result.current.hasSingleSignin()).toBe(true);
  });

  it('shouldShowExternalLoginsTab returns false in readonly mode', async () => {
    vi.mocked(useQuayConfig).mockReturnValue({
      external_login: [{id: 'github', title: 'GitHub', icon: ''}],
      features: {DIRECT_LOGIN: true},
      config: {},
      registry_state: 'readonly',
    } as any);
    const {result} = renderHook(() => useExternalLogins());
    await waitFor(() => expect(result.current.externalLogins).toHaveLength(1));
    expect(result.current.shouldShowExternalLoginsTab()).toBe(false);
  });
});
