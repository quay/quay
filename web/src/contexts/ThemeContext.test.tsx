import {renderHook, act} from '@testing-library/react';
import React from 'react';
import {ThemeProvider, ThemePreference, useTheme} from './ThemeContext';

/**
 * Creates a stable matchMedia mock object. Returns the same object on every
 * window.matchMedia() call within a test, which is required because
 * ThemeContext calls matchMedia at component body scope (re-called on render).
 */
function createMockMediaQueryList(prefersDark: boolean) {
  const listeners: Array<(e: MediaQueryListEvent) => void> = [];
  const mql = {
    matches: prefersDark,
    media: '(prefers-color-scheme: dark)',
    onchange: null,
    addListener: vi.fn(),
    removeListener: vi.fn(),
    addEventListener: vi.fn(
      (_event: string, cb: (e: MediaQueryListEvent) => void) => {
        listeners.push(cb);
      },
    ),
    removeEventListener: vi.fn(
      (_event: string, cb: (e: MediaQueryListEvent) => void) => {
        const idx = listeners.indexOf(cb);
        if (idx >= 0) listeners.splice(idx, 1);
      },
    ),
    dispatchEvent: vi.fn(),
  };

  /** Simulates a system theme change by invoking all registered listeners. */
  function triggerChange(newMatches: boolean) {
    mql.matches = newMatches;
    listeners.forEach((cb) => cb({matches: newMatches} as MediaQueryListEvent));
  }

  return {mql, triggerChange};
}

/** Wrapper component that provides ThemeContext for renderHook tests. */
function wrapper({children}: {children: React.ReactNode}) {
  return <ThemeProvider>{children}</ThemeProvider>;
}

describe('ThemeContext', () => {
  let mockMql: ReturnType<typeof createMockMediaQueryList>;

  beforeEach(() => {
    localStorage.clear();
    document.documentElement.classList.remove('pf-v6-theme-dark');
    mockMql = createMockMediaQueryList(false);
    vi.spyOn(window, 'matchMedia').mockReturnValue(
      mockMql.mql as unknown as MediaQueryList,
    );
  });

  afterEach(() => {
    localStorage.clear();
    document.documentElement.classList.remove('pf-v6-theme-dark');
  });

  describe('default state', () => {
    it('defaults to AUTO preference when localStorage is empty', () => {
      const {result} = renderHook(() => useTheme(), {wrapper});
      expect(result.current.themePreference).toBe(ThemePreference.AUTO);
    });

    it('defaults isDarkTheme to false when system prefers light', () => {
      const {result} = renderHook(() => useTheme(), {wrapper});
      expect(result.current.isDarkTheme).toBe(false);
    });

    it('defaults isDarkTheme to true when system prefers dark', () => {
      mockMql = createMockMediaQueryList(true);
      vi.spyOn(window, 'matchMedia').mockReturnValue(
        mockMql.mql as unknown as MediaQueryList,
      );

      const {result} = renderHook(() => useTheme(), {wrapper});
      expect(result.current.isDarkTheme).toBe(true);
    });
  });

  describe('localStorage initialization', () => {
    it('reads LIGHT from localStorage', () => {
      localStorage.setItem('theme-preference', 'LIGHT');
      const {result} = renderHook(() => useTheme(), {wrapper});
      expect(result.current.themePreference).toBe(ThemePreference.LIGHT);
      expect(result.current.isDarkTheme).toBe(false);
    });

    it('reads DARK from localStorage', () => {
      localStorage.setItem('theme-preference', 'DARK');
      const {result} = renderHook(() => useTheme(), {wrapper});
      expect(result.current.themePreference).toBe(ThemePreference.DARK);
      expect(result.current.isDarkTheme).toBe(true);
    });

    it('reads AUTO from localStorage', () => {
      localStorage.setItem('theme-preference', 'AUTO');
      const {result} = renderHook(() => useTheme(), {wrapper});
      expect(result.current.themePreference).toBe(ThemePreference.AUTO);
    });

    it('falls back to AUTO for invalid localStorage value', () => {
      localStorage.setItem('theme-preference', 'INVALID');
      const {result} = renderHook(() => useTheme(), {wrapper});
      expect(result.current.themePreference).toBe(ThemePreference.AUTO);
    });
  });

  describe('setThemePreference', () => {
    it('switches from AUTO to LIGHT', () => {
      const {result} = renderHook(() => useTheme(), {wrapper});

      act(() => {
        result.current.setThemePreference(ThemePreference.LIGHT);
      });

      expect(result.current.themePreference).toBe(ThemePreference.LIGHT);
      expect(result.current.isDarkTheme).toBe(false);
    });

    it('switches from AUTO to DARK', () => {
      const {result} = renderHook(() => useTheme(), {wrapper});

      act(() => {
        result.current.setThemePreference(ThemePreference.DARK);
      });

      expect(result.current.themePreference).toBe(ThemePreference.DARK);
      expect(result.current.isDarkTheme).toBe(true);
    });

    it('switches from DARK to LIGHT', () => {
      localStorage.setItem('theme-preference', 'DARK');
      const {result} = renderHook(() => useTheme(), {wrapper});
      expect(result.current.isDarkTheme).toBe(true);

      act(() => {
        result.current.setThemePreference(ThemePreference.LIGHT);
      });

      expect(result.current.isDarkTheme).toBe(false);
    });

    it('switches from LIGHT to AUTO with system=light', () => {
      localStorage.setItem('theme-preference', 'LIGHT');
      const {result} = renderHook(() => useTheme(), {wrapper});

      act(() => {
        result.current.setThemePreference(ThemePreference.AUTO);
      });

      expect(result.current.themePreference).toBe(ThemePreference.AUTO);
      expect(result.current.isDarkTheme).toBe(false);
    });

    it('switches from LIGHT to AUTO with system=dark', () => {
      mockMql = createMockMediaQueryList(true);
      vi.spyOn(window, 'matchMedia').mockReturnValue(
        mockMql.mql as unknown as MediaQueryList,
      );
      localStorage.setItem('theme-preference', 'LIGHT');
      const {result} = renderHook(() => useTheme(), {wrapper});

      act(() => {
        result.current.setThemePreference(ThemePreference.AUTO);
      });

      expect(result.current.themePreference).toBe(ThemePreference.AUTO);
      expect(result.current.isDarkTheme).toBe(true);
    });
  });

  describe('localStorage persistence', () => {
    it('persists LIGHT to localStorage', () => {
      const {result} = renderHook(() => useTheme(), {wrapper});

      act(() => {
        result.current.setThemePreference(ThemePreference.LIGHT);
      });

      expect(localStorage.getItem('theme-preference')).toBe('LIGHT');
    });

    it('persists DARK to localStorage', () => {
      const {result} = renderHook(() => useTheme(), {wrapper});

      act(() => {
        result.current.setThemePreference(ThemePreference.DARK);
      });

      expect(localStorage.getItem('theme-preference')).toBe('DARK');
    });

    it('persists AUTO to localStorage', () => {
      localStorage.setItem('theme-preference', 'DARK');
      const {result} = renderHook(() => useTheme(), {wrapper});

      act(() => {
        result.current.setThemePreference(ThemePreference.AUTO);
      });

      expect(localStorage.getItem('theme-preference')).toBe('AUTO');
    });
  });

  describe('DOM class updates', () => {
    it('adds pf-v6-theme-dark class when dark theme is active', () => {
      const {result} = renderHook(() => useTheme(), {wrapper});

      act(() => {
        result.current.setThemePreference(ThemePreference.DARK);
      });

      expect(
        document.documentElement.classList.contains('pf-v6-theme-dark'),
      ).toBe(true);
    });

    it('removes pf-v6-theme-dark class when switching to light', () => {
      localStorage.setItem('theme-preference', 'DARK');
      const {result} = renderHook(() => useTheme(), {wrapper});
      expect(
        document.documentElement.classList.contains('pf-v6-theme-dark'),
      ).toBe(true);

      act(() => {
        result.current.setThemePreference(ThemePreference.LIGHT);
      });

      expect(
        document.documentElement.classList.contains('pf-v6-theme-dark'),
      ).toBe(false);
    });

    it('does not have dark class when system=light and theme=AUTO', () => {
      const {result} = renderHook(() => useTheme(), {wrapper});
      expect(result.current.themePreference).toBe(ThemePreference.AUTO);
      expect(
        document.documentElement.classList.contains('pf-v6-theme-dark'),
      ).toBe(false);
    });
  });

  describe('matchMedia listener (AUTO mode)', () => {
    it('registers event listener in AUTO mode', () => {
      renderHook(() => useTheme(), {wrapper});
      expect(mockMql.mql.addEventListener).toHaveBeenCalledWith(
        'change',
        expect.any(Function),
      );
    });

    it('responds to system theme change from light to dark', () => {
      const {result} = renderHook(() => useTheme(), {wrapper});
      expect(result.current.isDarkTheme).toBe(false);

      act(() => {
        mockMql.triggerChange(true);
      });

      expect(result.current.isDarkTheme).toBe(true);
    });

    it('removes event listener when switching away from AUTO', () => {
      const {result} = renderHook(() => useTheme(), {wrapper});

      act(() => {
        result.current.setThemePreference(ThemePreference.DARK);
      });

      expect(mockMql.mql.removeEventListener).toHaveBeenCalledWith(
        'change',
        expect.any(Function),
      );
    });

    it('removes event listener on unmount in AUTO mode', () => {
      const {unmount} = renderHook(() => useTheme(), {wrapper});

      unmount();

      expect(mockMql.mql.removeEventListener).toHaveBeenCalledWith(
        'change',
        expect.any(Function),
      );
    });
  });

  describe('useTheme without provider', () => {
    it('returns default context values without provider', () => {
      const {result} = renderHook(() => useTheme());
      expect(result.current.themePreference).toBe(ThemePreference.AUTO);
      expect(result.current.isDarkTheme).toBe(false);
      expect(typeof result.current.setThemePreference).toBe('function');
    });
  });
});
