import {useState, useMemo} from 'react';
import {QuayThSortProps as ThProps} from '../components/QuayTable';

export interface PaginatedSortableTableConfig<T> {
  columns: Record<number, (item: T) => string | number>;
  initialSort?: {columnIndex: number; direction: 'asc' | 'desc'};
  filter?: (item: T) => boolean;
  initialPerPage?: number;
}

/**
 * Unified hook for sortable, paginated, filterable tables
 *
 * Combines sorting, pagination, and filtering logic into a single reusable hook.
 * Replaces the need for separate useTableSort + pagination boilerplate.
 *
 * @param data - Array of data to be processed
 * @param config - Configuration object with columns, sorting, filtering options
 * @returns Complete table state and controls
 *
 * @example
 * const {paginatedData, getSortableSort, paginationProps} = usePaginatedSortableTable(
 *   repositories,
 *   {
 *     columns: {
 *       0: (repo) => repo.name,
 *       1: (repo) => repo.is_public ? 'public' : 'private',
 *     },
 *     initialSort: {columnIndex: 0, direction: 'asc'},
 *     filter: searchFilter,
 *   }
 * );
 */
export function usePaginatedSortableTable<T>(
  data: T[],
  config: PaginatedSortableTableConfig<T>,
) {
  const {columns, initialSort, filter, initialPerPage = 20} = config;

  // Pagination state
  const [page, setPage] = useState<number>(1);
  const [perPage, setPerPage] = useState<number>(initialPerPage);

  // Sorting state
  const [activeSortIndex, setActiveSortIndex] = useState<number | null>(
    initialSort?.columnIndex ?? null,
  );
  const [activeSortDirection, setActiveSortDirection] = useState<
    'asc' | 'desc' | null
  >(initialSort?.direction ?? null);

  // Sort handler function
  const handleSort = (
    _event: React.MouseEvent,
    index: number,
    direction: 'asc' | 'desc',
  ) => {
    setActiveSortIndex(index);
    setActiveSortDirection(direction);
    // Reset to page 1 when sort changes
    setPage(1);
  };

  // Sort helper function for PatternFly
  const getSortableSort = (columnIndex: number): ThProps['sort'] => ({
    sortBy: {
      index: activeSortIndex,
      direction: activeSortDirection,
    },
    onSort: handleSort,
    columnIndex,
  });

  // Process data: filter → sort → paginate
  const processedData = useMemo(() => {
    // Step 1: Apply filtering
    const filteredData = filter ? data.filter(filter) : data;

    // Step 2: Apply sorting
    const sortedData = filteredData ? [...filteredData] : [];
    if (
      activeSortIndex !== null &&
      activeSortDirection !== null &&
      sortedData.length > 0 &&
      columns[activeSortIndex]
    ) {
      sortedData.sort((a, b) => {
        const extractValue = columns[activeSortIndex];
        const aValue = extractValue(a);
        const bValue = extractValue(b);

        let result = 0;
        if (typeof aValue === 'string' && typeof bValue === 'string') {
          result = aValue.localeCompare(bValue);
        } else if (typeof aValue === 'number' && typeof bValue === 'number') {
          result = aValue - bValue;
        }

        return activeSortDirection === 'desc' ? -result : result;
      });
    }

    // Step 3: Apply pagination
    const paginatedData = sortedData.slice(
      page * perPage - perPage,
      page * perPage - perPage + perPage,
    );

    return {
      filteredData,
      sortedData,
      paginatedData,
    };
  }, [
    data,
    filter,
    activeSortIndex,
    activeSortDirection,
    columns,
    page,
    perPage,
  ]);

  // Convenience props object for ToolbarPagination
  const paginationProps = {
    total: processedData.filteredData.length,
    itemsList: processedData.filteredData,
    perPage,
    page,
    setPage,
    setPerPage,
  };

  return {
    // Processed data
    paginatedData: processedData.paginatedData,
    filteredData: processedData.filteredData,
    sortedData: processedData.sortedData,

    // Sort controls
    getSortableSort,

    // Pagination controls
    page,
    perPage,
    setPage,
    setPerPage,
    totalCount: processedData.filteredData.length,

    // Convenience props
    paginationProps,
  };
}
