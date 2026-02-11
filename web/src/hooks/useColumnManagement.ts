import {useState, useCallback, useMemo, useEffect} from 'react';
import type {
  ColumnConfig,
  UseColumnManagementReturn,
  UseColumnManagementOptions,
} from 'src/components/ManageColumns/types';

/**
 * Merge stored config with defaults to handle schema changes.
 * Preserves visibility from stored config but updates other properties from defaults.
 */
function mergeWithDefaults(
  stored: ColumnConfig[],
  defaults: ColumnConfig[],
): ColumnConfig[] {
  const storedMap = new Map(stored.map((c) => [c.id, c]));
  return defaults.map((def) => {
    const storedCol = storedMap.get(def.id);
    if (storedCol) {
      return {...def, isVisible: storedCol.isVisible};
    }
    return def;
  });
}

/**
 * Hook for managing table column visibility with localStorage persistence.
 *
 * @example
 * const {columns, visibleColumns, saveColumns, restoreDefaults, isColumnVisible} = useColumnManagement({
 *   storageKey: 'repositories-list',
 *   defaultColumns: [
 *     {id: 'name', title: 'Name', isVisible: true, isDefault: true, isDisabled: true},
 *     {id: 'visibility', title: 'Visibility', isVisible: true, isDefault: true},
 *     {id: 'size', title: 'Size', isVisible: true, isDefault: false},
 *     {id: 'lastModified', title: 'Last Modified', isVisible: true, isDefault: true},
 *   ],
 * });
 */
export function useColumnManagement(
  options: UseColumnManagementOptions,
): UseColumnManagementReturn {
  const {storageKey, defaultColumns} = options;
  const fullStorageKey = `quay-columns-${storageKey}`;

  // Initialize state from localStorage or defaults
  const [columns, setColumns] = useState<ColumnConfig[]>(() => {
    try {
      const stored = localStorage.getItem(fullStorageKey);
      if (stored) {
        const parsed = JSON.parse(stored) as ColumnConfig[];
        return mergeWithDefaults(parsed, defaultColumns);
      }
    } catch (e) {
      console.warn('Failed to parse stored column config:', e);
    }
    return defaultColumns;
  });

  // Persist to localStorage when columns change
  useEffect(() => {
    try {
      localStorage.setItem(fullStorageKey, JSON.stringify(columns));
    } catch (e) {
      console.warn('Failed to save column config:', e);
    }
  }, [columns, fullStorageKey]);

  // Computed: visible columns only
  const visibleColumns = useMemo(
    () => columns.filter((col) => col.isVisible),
    [columns],
  );

  const visibleCount = visibleColumns.length;

  // Check if specific column is visible
  const isColumnVisible = useCallback(
    (columnId: string) =>
      columns.find((c) => c.id === columnId)?.isVisible ?? false,
    [columns],
  );

  // Toggle single column visibility
  const toggleColumn = useCallback((columnId: string) => {
    setColumns((prev) =>
      prev.map((col) =>
        col.id === columnId && !col.isDisabled
          ? {...col, isVisible: !col.isVisible}
          : col,
      ),
    );
  }, []);

  // Set specific column visibility
  const setColumnVisibility = useCallback(
    (columnId: string, isVisible: boolean) => {
      setColumns((prev) =>
        prev.map((col) =>
          col.id === columnId && !col.isDisabled ? {...col, isVisible} : col,
        ),
      );
    },
    [],
  );

  // Restore to default configuration
  const restoreDefaults = useCallback(() => {
    setColumns(defaultColumns);
  }, [defaultColumns]);

  // Save columns (for modal save action)
  const saveColumns = useCallback((newColumns: ColumnConfig[]) => {
    setColumns(newColumns);
  }, []);

  return {
    columns,
    visibleColumns,
    isColumnVisible,
    toggleColumn,
    setColumnVisibility,
    restoreDefaults,
    saveColumns,
    visibleCount,
  };
}
