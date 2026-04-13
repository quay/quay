/**
 * Unit tests for the useLogo hook.
 *
 * All React hook dependencies (useQuayConfig, useTheme) are fully mocked, so
 * useLogo() can be called directly without a React component or renderHook.
 * SVG imports are stubbed by jest.mock factories to return predictable strings.
 */

// Stub SVG assets so assertions can check which asset was selected.
// ts-jest compiles to CJS so default imports resolve to module.default.
jest.mock('src/assets/logo-dark.svg', () => ({
  __esModule: true,
  default: 'logo-dark.svg',
}));
jest.mock('src/assets/logo.svg', () => ({
  __esModule: true,
  default: 'logo.svg',
}));
jest.mock('src/assets/RH_QuayIO2.svg', () => ({
  __esModule: true,
  default: 'RH_QuayIO2.svg',
}));
jest.mock('src/assets/RH_QuayIO.svg', () => ({
  __esModule: true,
  default: 'RH_QuayIO.svg',
}));

// Mock hook dependencies with explicit factories so Jest never loads the real
// modules (which pull in axios.ts that accesses window.location at import time).
const mockUseQuayConfig = jest.fn();
const mockUseTheme = jest.fn();

jest.mock('src/hooks/UseQuayConfig', () => ({
  useQuayConfig: mockUseQuayConfig,
}));

jest.mock('src/contexts/ThemeContext', () => ({
  useTheme: mockUseTheme,
}));

import {useLogo} from './UseLogo';

function setup(
  hostname: string,
  isDarkTheme: boolean,
  branding?: {logo?: string; logo_dark?: string},
) {
  // In jest-environment-node there is no window global; set it up manually.
  (global as any).window = {location: {hostname}};
  mockUseTheme.mockReturnValue({isDarkTheme});
  mockUseQuayConfig.mockReturnValue(
    branding !== undefined ? {config: {BRANDING: branding}} : {config: {}},
  );
}

describe('useLogo', () => {
  afterEach(() => {
    jest.clearAllMocks();
  });

  describe('Priority 1 — quay.io / stage.quay.io hostnames', () => {
    it('returns RH_QuayIO2.svg (dark) on quay.io in dark mode', () => {
      setup('quay.io', true);
      expect(useLogo()).toBe('RH_QuayIO2.svg');
    });

    it('returns RH_QuayIO.svg (light) on quay.io in light mode', () => {
      setup('quay.io', false);
      expect(useLogo()).toBe('RH_QuayIO.svg');
    });

    it('returns RH_QuayIO2.svg (dark) on stage.quay.io in dark mode', () => {
      setup('stage.quay.io', true);
      expect(useLogo()).toBe('RH_QuayIO2.svg');
    });

    it('returns RH_QuayIO.svg (light) on stage.quay.io in light mode', () => {
      setup('stage.quay.io', false);
      expect(useLogo()).toBe('RH_QuayIO.svg');
    });
  });

  describe('Priority 2 — BRANDING.logo_dark configured', () => {
    it('returns BRANDING.logo_dark when dark mode is active', () => {
      setup('self-hosted.example.com', true, {
        logo: '/custom/light.svg',
        logo_dark: '/custom/dark.svg',
      });
      expect(useLogo()).toBe('/custom/dark.svg');
    });
  });

  describe('Priority 3 — BRANDING.logo configured (light mode only)', () => {
    it('returns BRANDING.logo in light mode', () => {
      setup('self-hosted.example.com', false, {logo: '/custom/light.svg'});
      expect(useLogo()).toBe('/custom/light.svg');
    });

    it('falls back to default dark logo in dark mode when BRANDING.logo_dark is absent', () => {
      // Regression test for PROJQUAY-11257: previously returned BRANDING.logo
      // (light-colored) even when dark mode was active, making the text invisible.
      setup('self-hosted.example.com', true, {logo: '/custom/light.svg'});
      expect(useLogo()).toBe('logo-dark.svg');
    });
  });

  describe('Priority 4 — no BRANDING configured (downstream default)', () => {
    it('returns logo-dark.svg in dark mode', () => {
      setup('self-hosted.example.com', true);
      expect(useLogo()).toBe('logo-dark.svg');
    });

    it('returns logo.svg in light mode', () => {
      setup('self-hosted.example.com', false);
      expect(useLogo()).toBe('logo.svg');
    });
  });
});
