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

const mockTheme = (isDark: boolean) =>
  vi.mocked(useTheme).mockReturnValue({
    isDarkTheme: isDark,
    themePreference: isDark ? 'DARK' : 'LIGHT',
    setThemePreference: vi.fn(),
  });

const mockBranding = (branding: Record<string, string> | undefined) =>
  vi
    .mocked(useQuayConfig)
    .mockReturnValue(
      branding
        ? ({config: {BRANDING: branding}} as ReturnType<typeof useQuayConfig>)
        : null,
    );

describe('useLogo', () => {
  it('returns logo_dark in dark mode when configured', () => {
    mockTheme(true);
    mockBranding({logo: '/light.svg', logo_dark: '/dark.svg'});
    const {result} = renderHook(() => useLogo());
    expect(result.current).toBe('/dark.svg');
  });

  it('returns logo in light mode', () => {
    mockTheme(false);
    mockBranding({logo: '/light.svg', logo_dark: '/dark.svg'});
    const {result} = renderHook(() => useLogo());
    expect(result.current).toBe('/light.svg');
  });

  it('falls back to logo in dark mode when logo_dark not set', () => {
    mockTheme(true);
    mockBranding({logo: '/light.svg'});
    const {result} = renderHook(() => useLogo());
    expect(result.current).toBe('/light.svg');
  });

  it('returns empty string when no branding config', () => {
    mockTheme(false);
    mockBranding(undefined);
    const {result} = renderHook(() => useLogo());
    expect(result.current).toBe('');
  });
});
