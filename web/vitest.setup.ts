// eslint-disable-next-line import/no-unresolved
import '@testing-library/jest-dom/vitest';

beforeEach(() => {
  // Guarded: playwright/utils/*.test.ts run under the node environment,
  // which has no localStorage/sessionStorage globals.
  if (typeof localStorage !== 'undefined') {
    localStorage.clear();
    sessionStorage.clear();
  }
});

// PatternFly components use window.matchMedia internally.
// happy-dom has partial support; this mock prevents errors.
// Guarded: playwright/utils/*.test.ts run under the node environment, which
// has no window global.
if (typeof window !== 'undefined') {
  Object.defineProperty(window, 'matchMedia', {
    writable: true,
    value: vi.fn().mockImplementation((query: string) => ({
      matches: false,
      media: query,
      onchange: null,
      addListener: vi.fn(),
      removeListener: vi.fn(),
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
      dispatchEvent: vi.fn(),
    })),
  });
}
