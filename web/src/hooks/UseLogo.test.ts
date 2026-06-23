import {renderHook} from '@testing-library/react';
import {useLogo} from './UseLogo';
import {useQuayConfig} from './UseQuayConfig';
import {useTheme} from 'src/contexts/ThemeContext';

vi.mock('./UseQuayConfig', () => ({
  useQuayConfig: vi.fn(),
}));

vi.mock('src/contexts/ThemeContext', () => ({
  useTheme: vi.fn(),
}));

vi.mock('src/assets/RH_Logo_Quay_White_UX-horizontal.svg', () => ({
  default: 'logo-dark.svg',
}));
vi.mock('src/assets/RH_Logo_Quay_Black_UX-horizontal.svg', () => ({
  default: 'logo-light.svg',
}));
vi.mock('src/assets/RH_QuayIO2.svg', () => ({default: 'rh-dark.svg'}));
vi.mock('src/assets/RH_QuayIO.svg', () => ({default: 'rh-light.svg'}));

describe('useLogo', () => {
  const originalLocation = window.location;

  afterEach(() => {
    Object.defineProperty(window, 'location', {
      value: originalLocation,
      writable: true,
    });
  });

  function setHostname(hostname: string) {
    Object.defineProperty(window, 'location', {
      value: {...originalLocation, hostname},
      writable: true,
    });
  }

  it('returns dark Red Hat branding on quay.io in dark mode', () => {
    setHostname('quay.io');
    vi.mocked(useTheme).mockReturnValue({
      isDarkTheme: true,
      themePreference: 'DARK',
      setThemePreference: vi.fn(),
    });
    vi.mocked(useQuayConfig).mockReturnValue(null);
    const {result} = renderHook(() => useLogo());
    expect(result.current).toBe('rh-dark.svg');
  });

  it('returns light Red Hat branding on quay.io in light mode', () => {
    setHostname('quay.io');
    vi.mocked(useTheme).mockReturnValue({
      isDarkTheme: false,
      themePreference: 'LIGHT',
      setThemePreference: vi.fn(),
    });
    vi.mocked(useQuayConfig).mockReturnValue(null);
    const {result} = renderHook(() => useLogo());
    expect(result.current).toBe('rh-light.svg');
  });

  it('returns default dark logo for downstream in dark mode', () => {
    setHostname('registry.example.com');
    vi.mocked(useTheme).mockReturnValue({
      isDarkTheme: true,
      themePreference: 'DARK',
      setThemePreference: vi.fn(),
    });
    vi.mocked(useQuayConfig).mockReturnValue({config: {}} as any);
    const {result} = renderHook(() => useLogo());
    expect(result.current).toBe('logo-dark.svg');
  });

  it('returns default light logo for downstream in light mode', () => {
    setHostname('registry.example.com');
    vi.mocked(useTheme).mockReturnValue({
      isDarkTheme: false,
      themePreference: 'LIGHT',
      setThemePreference: vi.fn(),
    });
    vi.mocked(useQuayConfig).mockReturnValue({config: {}} as any);
    const {result} = renderHook(() => useLogo());
    expect(result.current).toBe('logo-light.svg');
  });

  it('uses BRANDING.logo_dark when configured and dark mode active', () => {
    setHostname('registry.example.com');
    vi.mocked(useTheme).mockReturnValue({
      isDarkTheme: true,
      themePreference: 'DARK',
      setThemePreference: vi.fn(),
    });
    vi.mocked(useQuayConfig).mockReturnValue({
      config: {
        BRANDING: {logo: '/custom-light.png', logo_dark: '/custom-dark.png'},
      },
    } as any);
    const {result} = renderHook(() => useLogo());
    expect(result.current).toBe('/custom-dark.png');
  });

  it('falls back to BRANDING.logo when logo_dark is not configured', () => {
    setHostname('registry.example.com');
    vi.mocked(useTheme).mockReturnValue({
      isDarkTheme: true,
      themePreference: 'DARK',
      setThemePreference: vi.fn(),
    });
    vi.mocked(useQuayConfig).mockReturnValue({
      config: {BRANDING: {logo: '/custom-light.png'}},
    } as any);
    const {result} = renderHook(() => useLogo());
    expect(result.current).toBe('/custom-light.png');
  });
});
