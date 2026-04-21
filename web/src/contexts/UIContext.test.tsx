import {renderHook, act} from '@testing-library/react';
import React from 'react';
import {UIProvider, useUI, AlertVariant} from './UIContext';

/** Wrapper component that provides UIContext for renderHook tests. */
function wrapper({children}: {children: React.ReactNode}) {
  return <UIProvider>{children}</UIProvider>;
}

describe('UIContext', () => {
  describe('sidebar state', () => {
    it('defaults to open when localStorage is empty', () => {
      const {result} = renderHook(() => useUI(), {wrapper});
      expect(result.current.isSidebarOpen).toBe(true);
    });

    it('reads initial state from localStorage (open)', () => {
      localStorage.setItem('quay-sidebar-open', 'true');
      const {result} = renderHook(() => useUI(), {wrapper});
      expect(result.current.isSidebarOpen).toBe(true);
    });

    it('reads initial state from localStorage (closed)', () => {
      localStorage.setItem('quay-sidebar-open', 'false');
      const {result} = renderHook(() => useUI(), {wrapper});
      expect(result.current.isSidebarOpen).toBe(false);
    });

    it('toggleSidebar flips state from open to closed', () => {
      const {result} = renderHook(() => useUI(), {wrapper});
      expect(result.current.isSidebarOpen).toBe(true);

      act(() => {
        result.current.toggleSidebar();
      });
      expect(result.current.isSidebarOpen).toBe(false);
    });

    it('toggleSidebar flips state from closed to open', () => {
      localStorage.setItem('quay-sidebar-open', 'false');
      const {result} = renderHook(() => useUI(), {wrapper});
      expect(result.current.isSidebarOpen).toBe(false);

      act(() => {
        result.current.toggleSidebar();
      });
      expect(result.current.isSidebarOpen).toBe(true);
    });

    it('persists sidebar state to localStorage on toggle', () => {
      const {result} = renderHook(() => useUI(), {wrapper});

      act(() => {
        result.current.toggleSidebar();
      });
      expect(localStorage.getItem('quay-sidebar-open')).toBe('false');

      act(() => {
        result.current.toggleSidebar();
      });
      expect(localStorage.getItem('quay-sidebar-open')).toBe('true');
    });

    it('double toggle returns to original state', () => {
      const {result} = renderHook(() => useUI(), {wrapper});
      expect(result.current.isSidebarOpen).toBe(true);

      act(() => {
        result.current.toggleSidebar();
        result.current.toggleSidebar();
      });
      expect(result.current.isSidebarOpen).toBe(true);
    });
  });

  describe('alert management', () => {
    it('starts with empty alerts', () => {
      const {result} = renderHook(() => useUI(), {wrapper});
      expect(result.current.alerts).toEqual([]);
    });

    it('addAlert appends a success alert with explicit key', () => {
      const {result} = renderHook(() => useUI(), {wrapper});

      act(() => {
        result.current.addAlert({
          variant: AlertVariant.Success,
          title: 'Created repo',
          key: 'alert-1',
        });
      });

      expect(result.current.alerts).toHaveLength(1);
      expect(result.current.alerts[0]).toMatchObject({
        variant: AlertVariant.Success,
        title: 'Created repo',
        key: 'alert-1',
      });
    });

    it('addAlert appends a failure alert with message', () => {
      const {result} = renderHook(() => useUI(), {wrapper});

      act(() => {
        result.current.addAlert({
          variant: AlertVariant.Failure,
          title: 'Failed to delete',
          key: 'err-1',
          message: 'Permission denied',
        });
      });

      expect(result.current.alerts).toHaveLength(1);
      expect(result.current.alerts[0]).toMatchObject({
        variant: AlertVariant.Failure,
        title: 'Failed to delete',
        message: 'Permission denied',
      });
    });

    it('addAlert generates a key when none is provided', () => {
      const {result} = renderHook(() => useUI(), {wrapper});

      act(() => {
        result.current.addAlert({
          variant: AlertVariant.Success,
          title: 'No key provided',
        });
      });

      expect(result.current.alerts).toHaveLength(1);
      expect(result.current.alerts[0].key).toBeDefined();
      expect(result.current.alerts[0].key).not.toBe('');
    });

    it('addAlert accumulates multiple alerts in order', () => {
      const {result} = renderHook(() => useUI(), {wrapper});

      act(() => {
        result.current.addAlert({
          variant: AlertVariant.Success,
          title: 'First',
          key: 'a1',
        });
        result.current.addAlert({
          variant: AlertVariant.Failure,
          title: 'Second',
          key: 'a2',
        });
        result.current.addAlert({
          variant: AlertVariant.Success,
          title: 'Third',
          key: 'a3',
        });
      });

      expect(result.current.alerts).toHaveLength(3);
      expect(result.current.alerts.map((a) => a.title)).toEqual([
        'First',
        'Second',
        'Third',
      ]);
    });

    it('removeAlert removes by key and ignores nonexistent keys', () => {
      const {result} = renderHook(() => useUI(), {wrapper});

      act(() => {
        result.current.addAlert({
          variant: AlertVariant.Success,
          title: 'Keep',
          key: 'keep',
        });
        result.current.addAlert({
          variant: AlertVariant.Failure,
          title: 'Remove',
          key: 'remove',
        });
      });

      act(() => {
        result.current.removeAlert('remove');
      });
      expect(result.current.alerts).toHaveLength(1);
      expect(result.current.alerts[0].key).toBe('keep');

      act(() => {
        result.current.removeAlert('nonexistent');
      });
      expect(result.current.alerts).toHaveLength(1);
    });

    it('clearAllAlerts empties array and is a no-op on empty', () => {
      const {result} = renderHook(() => useUI(), {wrapper});

      act(() => {
        result.current.addAlert({
          variant: AlertVariant.Success,
          title: 'One',
          key: 'k1',
        });
        result.current.addAlert({
          variant: AlertVariant.Failure,
          title: 'Two',
          key: 'k2',
        });
      });
      expect(result.current.alerts).toHaveLength(2);

      act(() => {
        result.current.clearAllAlerts();
      });
      expect(result.current.alerts).toEqual([]);

      act(() => {
        result.current.clearAllAlerts();
      });
      expect(result.current.alerts).toEqual([]);
    });
  });

  describe('useUI outside provider', () => {
    it('throws when used outside UIProvider', () => {
      // eslint-disable-next-line @typescript-eslint/no-empty-function
      const spy = vi.spyOn(console, 'error').mockImplementation(() => {});

      expect(() => {
        renderHook(() => useUI());
      }).toThrow('useUI must be used within a UIProvider');

      spy.mockRestore();
    });
  });
});
