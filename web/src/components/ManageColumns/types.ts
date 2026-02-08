/**
 * Configuration for a single column in a table
 */
export interface ColumnConfig {
  /** Unique identifier for the column */
  id: string;
  /** Display name shown in the table header and modal */
  title: string;
  /** Whether this column is currently visible */
  isVisible: boolean;
  /** Whether this is a default column (shown in left section of modal) */
  isDefault: boolean;
  /** Whether the column can be hidden (some columns like "Name" should always be visible) */
  isDisabled?: boolean;
  /** Sort index for the column (for use with usePaginatedSortableTable) */
  sortIndex?: number;
}

/**
 * Props for the ManageColumnsModal component
 */
export interface ManageColumnsModalProps {
  /** Whether the modal is open */
  isOpen: boolean;
  /** Callback when the modal should close */
  onClose: () => void;
  /** Current column configurations */
  columns: ColumnConfig[];
  /** Callback when columns are saved - receives updated column configs */
  onSave: (columns: ColumnConfig[]) => void;
  /** Maximum number of visible columns (displays info alert) */
  maxVisibleColumns?: number;
  /** Title for the modal (defaults to "Manage columns") */
  title?: string;
}

/**
 * Return type for the useColumnManagement hook
 */
export interface UseColumnManagementReturn {
  /** Current column configurations */
  columns: ColumnConfig[];
  /** Get visible columns only */
  visibleColumns: ColumnConfig[];
  /** Check if a specific column is visible */
  isColumnVisible: (columnId: string) => boolean;
  /** Toggle visibility of a single column */
  toggleColumn: (columnId: string) => void;
  /** Set visibility for a specific column */
  setColumnVisibility: (columnId: string, isVisible: boolean) => void;
  /** Restore all columns to their default visibility */
  restoreDefaults: () => void;
  /** Save column configuration (persists to localStorage) */
  saveColumns: (columns: ColumnConfig[]) => void;
  /** Count of currently visible columns */
  visibleCount: number;
}

/**
 * Options for the useColumnManagement hook
 */
export interface UseColumnManagementOptions {
  /** Unique storage key for localStorage persistence */
  storageKey: string;
  /** Default column configurations (used on first load and for restore) */
  defaultColumns: ColumnConfig[];
}
