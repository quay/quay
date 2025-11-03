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
  const [isSidebarOpen, setIsSidebarOpen] = useState<boolean>(() => {
    const stored = localStorage.getItem('quay-sidebar-open');
    return stored !== null ? stored === 'true' : true; // Default to open
  });

  // Alert state
  const [alerts, setAlerts] = useState<AlertDetails[]>([]);

  // Persist sidebar state to localStorage
  useEffect(() => {
    localStorage.setItem('quay-sidebar-open', String(isSidebarOpen));
  }, [isSidebarOpen]);

  const toggleSidebar = useCallback(() => {
    setIsSidebarOpen((prev) => !prev);
  }, []);

  const addAlert = useCallback((alert: AlertDetails) => {
    const alertWithKey = {
      ...alert,
      key: alert.key ?? crypto.randomUUID(),
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
