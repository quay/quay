import React, {
  createContext,
  useContext,
  useState,
  useEffect,
  useCallback,
  useMemo,
  ReactNode,
} from 'react';

export enum AlertVariant {
  Success = 'success',
  Failure = 'danger',
}

export interface AlertDetails {
  variant: AlertVariant;
  title: string;
  key?: string;
  message?: string | ReactNode;
}

interface UIContextType {
  // Sidebar state
  isSidebarOpen: boolean;
  toggleSidebar: () => void;
  setIsMobileView: (isMobileView: boolean) => void;

  // Alert state
  alerts: AlertDetails[];
  addAlert: (alert: AlertDetails) => void;
  removeAlert: (key: string) => void;
  clearAllAlerts: () => void;
}

const UIContext = createContext<UIContextType | undefined>(undefined);

interface UIProviderProps {
  children: React.ReactNode;
}

export function UIProvider({children}: UIProviderProps) {
  // Sidebar state with localStorage persistence
  const [isDesktopSidebarOpen, setIsDesktopSidebarOpen] = useState<boolean>(
    () => {
      const stored = localStorage.getItem('quay-sidebar-open');
      return stored !== null ? stored === 'true' : true; // Default to open
    },
  );
  // Below PF's xl breakpoint the sidebar overlays content, so it starts
  // closed and is not persisted.
  const [isMobileSidebarOpen, setIsMobileSidebarOpen] = useState(false);
  const [isMobileView, setIsMobileView] = useState(false);
  const isSidebarOpen = isMobileView
    ? isMobileSidebarOpen
    : isDesktopSidebarOpen;

  // Alert state
  const [alerts, setAlerts] = useState<AlertDetails[]>([]);

  // Persist sidebar state to localStorage
  useEffect(() => {
    localStorage.setItem('quay-sidebar-open', String(isDesktopSidebarOpen));
  }, [isDesktopSidebarOpen]);

  const toggleSidebar = useCallback(() => {
    const setOpen = isMobileView
      ? setIsMobileSidebarOpen
      : setIsDesktopSidebarOpen;
    setOpen((prev) => !prev);
  }, [isMobileView]);

  const addAlert = useCallback((alert: AlertDetails) => {
    const alertWithKey = {
      ...alert,
      key: alert.key ?? Math.random().toString(36).substring(7),
    };
    setAlerts((prev) => [...prev, alertWithKey]);
  }, []);

  const removeAlert = useCallback((key: string) => {
    setAlerts((prev) => prev.filter((a) => a.key !== key));
  }, []);

  const clearAllAlerts = useCallback(() => {
    setAlerts([]);
  }, []);

  const value: UIContextType = useMemo(
    () => ({
      isSidebarOpen,
      toggleSidebar,
      setIsMobileView,
      alerts,
      addAlert,
      removeAlert,
      clearAllAlerts,
    }),
    [
      isSidebarOpen,
      toggleSidebar,
      alerts,
      addAlert,
      removeAlert,
      clearAllAlerts,
    ],
  );

  return <UIContext.Provider value={value}>{children}</UIContext.Provider>;
}

/**
 * Custom hook to access UI context
 * @returns UI context with sidebar state and future alert/theme state
 */
export function useUI(): UIContextType {
  const context = useContext(UIContext);
  if (context === undefined) {
    throw new Error('useUI must be used within a UIProvider');
  }
  return context;
}
