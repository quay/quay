import type React from 'react';
import {renderHook, act} from '@testing-library/react';
import {usePaginatedSortableTable} from './usePaginatedSortableTable';

interface TestItem {
  name: string;
  count: number;
  hexId: string;
}

const sampleItems: TestItem[] = [
  {name: 'banana', count: 5, hexId: 'bb22aa11'},
  {name: 'apple', count: 10, hexId: 'ff00cc33'},
  {name: 'cherry', count: 1, hexId: '00aabb11'},
  {name: 'date', count: 20, hexId: 'aa11bb22'},
];

const columns: Record<number, (item: TestItem) => string | number> = {
  0: (item) => item.name,
  1: (item) => item.count,
  2: (item) => item.hexId,
};

/**
 * Triggers a sort via the getSortableSort onSort handler, simulating
 * a PatternFly table header click.
 */
function triggerSort(
  result: {current: ReturnType<typeof usePaginatedSortableTable>},
  columnIndex: number,
  direction: 'asc' | 'desc',
) {
  const sortProps = result.current.getSortableSort(columnIndex);
  sortProps.onSort(null as unknown as React.MouseEvent, columnIndex, direction);
}

describe('usePaginatedSortableTable', () => {
  beforeEach(() => {
    localStorage.clear();
  });

  describe('default state', () => {
    it('initializes with page 1 and perPage 20', () => {
      const {result} = renderHook(() =>
        usePaginatedSortableTable(sampleItems, {columns}),
      );
      expect(result.current.page).toBe(1);
      expect(result.current.perPage).toBe(20);
    });

    it('has no active sort when no initialSort provided', () => {
      const {result} = renderHook(() =>
        usePaginatedSortableTable(sampleItems, {columns}),
      );
      const sortProps = result.current.getSortableSort(0);
      expect(sortProps.sortBy.index).toBeNull();
      expect(sortProps.sortBy.direction).toBeNull();
    });

    it('returns all data when it fits in one page', () => {
      const {result} = renderHook(() =>
        usePaginatedSortableTable(sampleItems, {columns}),
      );
      expect(result.current.paginatedData).toHaveLength(4);
      expect(result.current.totalCount).toBe(4);
    });

    it('returns empty arrays for empty data', () => {
      const {result} = renderHook(() =>
        usePaginatedSortableTable([], {columns}),
      );
      expect(result.current.paginatedData).toEqual([]);
      expect(result.current.filteredData).toEqual([]);
      expect(result.current.sortedData).toEqual([]);
      expect(result.current.totalCount).toBe(0);
    });
  });

  describe('initial configuration', () => {
    it('respects initialSort config', () => {
      const {result} = renderHook(() =>
        usePaginatedSortableTable(sampleItems, {
          columns,
          initialSort: {columnIndex: 0, direction: 'asc'},
        }),
      );
      // Sorted by name ascending: apple, banana, cherry, date
      expect(result.current.paginatedData[0].name).toBe('apple');
      expect(result.current.paginatedData[3].name).toBe('date');
    });

    it('respects custom initialPerPage', () => {
      const {result} = renderHook(() =>
        usePaginatedSortableTable(sampleItems, {
          columns,
          initialPerPage: 2,
        }),
      );
      expect(result.current.perPage).toBe(2);
      expect(result.current.paginatedData).toHaveLength(2);
    });
  });

  describe('string sorting', () => {
    it('sorts strings ascending via localeCompare', () => {
      const {result} = renderHook(() =>
        usePaginatedSortableTable(sampleItems, {columns}),
      );
      act(() => {
        triggerSort(result, 0, 'asc');
      });
      const names = result.current.paginatedData.map((i) => i.name);
      expect(names).toEqual(['apple', 'banana', 'cherry', 'date']);
    });

    it('sorts strings descending', () => {
      const {result} = renderHook(() =>
        usePaginatedSortableTable(sampleItems, {columns}),
      );
      act(() => {
        triggerSort(result, 0, 'desc');
      });
      const names = result.current.paginatedData.map((i) => i.name);
      expect(names).toEqual(['date', 'cherry', 'banana', 'apple']);
    });

    it('sorts numeric strings correctly with numeric option', () => {
      const items = [
        {name: 'item10', count: 0, hexId: 'aa'},
        {name: 'item2', count: 0, hexId: 'bb'},
        {name: 'item1', count: 0, hexId: 'cc'},
      ];
      const {result} = renderHook(() =>
        usePaginatedSortableTable(items, {columns}),
      );
      act(() => {
        triggerSort(result, 0, 'asc');
      });
      const names = result.current.paginatedData.map((i) => i.name);
      expect(names).toEqual(['item1', 'item2', 'item10']);
    });

    it('sorts case-insensitively', () => {
      const items = [
        {name: 'Banana', count: 0, hexId: 'aa'},
        {name: 'apple', count: 0, hexId: 'bb'},
        {name: 'Cherry', count: 0, hexId: 'cc'},
      ];
      const {result} = renderHook(() =>
        usePaginatedSortableTable(items, {columns}),
      );
      act(() => {
        triggerSort(result, 0, 'asc');
      });
      const names = result.current.paginatedData.map((i) => i.name);
      expect(names).toEqual(['apple', 'Banana', 'Cherry']);
    });
  });

  describe('hex string sorting', () => {
    it('detects hex strings and sorts by parsed first 8 chars', () => {
      const {result} = renderHook(() =>
        usePaginatedSortableTable(sampleItems, {columns}),
      );
      act(() => {
        triggerSort(result, 2, 'asc');
      });
      const ids = result.current.paginatedData.map((i) => i.hexId);
      // 00aabb11 < aa11bb22 < bb22aa11 < ff00cc33
      expect(ids).toEqual(['00aabb11', 'aa11bb22', 'bb22aa11', 'ff00cc33']);
    });

    it('sorts hex strings descending', () => {
      const {result} = renderHook(() =>
        usePaginatedSortableTable(sampleItems, {columns}),
      );
      act(() => {
        triggerSort(result, 2, 'desc');
      });
      const ids = result.current.paginatedData.map((i) => i.hexId);
      expect(ids).toEqual(['ff00cc33', 'bb22aa11', 'aa11bb22', '00aabb11']);
    });

    it('sorts mixed-case hex strings', () => {
      const items = [
        {name: 'a', count: 0, hexId: 'FF00AA00'},
        {name: 'b', count: 0, hexId: 'aa00ff00'},
        {name: 'c', count: 0, hexId: '00ff00aa'},
      ];
      const {result} = renderHook(() =>
        usePaginatedSortableTable(items, {columns}),
      );
      act(() => {
        triggerSort(result, 2, 'asc');
      });
      const ids = result.current.paginatedData.map((i) => i.hexId);
      expect(ids).toEqual(['00ff00aa', 'aa00ff00', 'FF00AA00']);
    });
  });

  describe('UUID sorting', () => {
    it('detects UUIDs and sorts by first 8 hex chars with hyphens stripped', () => {
      const items = [
        {
          name: 'c',
          count: 0,
          hexId: 'ff000000-1111-2222-3333-444444444444',
        },
        {
          name: 'a',
          count: 0,
          hexId: '00aabb00-1111-2222-3333-444444444444',
        },
        {
          name: 'b',
          count: 0,
          hexId: 'aa110000-1111-2222-3333-444444444444',
        },
      ];
      const uuidColumns: Record<number, (item: TestItem) => string | number> = {
        0: (item) => item.hexId,
      };
      const {result} = renderHook(() =>
        usePaginatedSortableTable(items, {columns: uuidColumns}),
      );
      act(() => {
        triggerSort(result, 0, 'asc');
      });
      const ids = result.current.paginatedData.map((i) => i.hexId);
      expect(ids).toEqual([
        '00aabb00-1111-2222-3333-444444444444',
        'aa110000-1111-2222-3333-444444444444',
        'ff000000-1111-2222-3333-444444444444',
      ]);
    });
  });

  describe('number sorting', () => {
    it('sorts numbers ascending', () => {
      const {result} = renderHook(() =>
        usePaginatedSortableTable(sampleItems, {columns}),
      );
      act(() => {
        triggerSort(result, 1, 'asc');
      });
      const counts = result.current.paginatedData.map((i) => i.count);
      expect(counts).toEqual([1, 5, 10, 20]);
    });

    it('sorts numbers descending', () => {
      const {result} = renderHook(() =>
        usePaginatedSortableTable(sampleItems, {columns}),
      );
      act(() => {
        triggerSort(result, 1, 'desc');
      });
      const counts = result.current.paginatedData.map((i) => i.count);
      expect(counts).toEqual([20, 10, 5, 1]);
    });
  });

  describe('sort interactions', () => {
    it('resets page to 1 when sort changes', () => {
      const manyItems = Array.from({length: 25}, (_, i) => ({
        name: `item${i}`,
        count: i,
        hexId: `0000000${i}`,
      }));
      const {result} = renderHook(() =>
        usePaginatedSortableTable(manyItems, {columns, initialPerPage: 10}),
      );
      act(() => {
        result.current.setPage(2);
      });
      expect(result.current.page).toBe(2);
      act(() => {
        triggerSort(result, 0, 'asc');
      });
      expect(result.current.page).toBe(1);
    });

    it('updates activeSortIndex and direction after onSort', () => {
      const {result} = renderHook(() =>
        usePaginatedSortableTable(sampleItems, {columns}),
      );
      act(() => {
        triggerSort(result, 1, 'desc');
      });
      const sortProps = result.current.getSortableSort(1);
      expect(sortProps.sortBy.index).toBe(1);
      expect(sortProps.sortBy.direction).toBe('desc');
    });

    it('handles missing column extractor gracefully', () => {
      const sparseColumns: Record<number, (item: TestItem) => string | number> =
        {
          0: (item) => item.name,
        };
      const {result} = renderHook(() =>
        usePaginatedSortableTable(sampleItems, {columns: sparseColumns}),
      );
      // Sort on column 5 which has no extractor
      act(() => {
        triggerSort(result, 5, 'asc');
      });
      // Should not crash, data returned in original order
      expect(result.current.paginatedData).toHaveLength(4);
    });
  });

  describe('getSortableSort', () => {
    it('returns object with sortBy, onSort, and columnIndex', () => {
      const {result} = renderHook(() =>
        usePaginatedSortableTable(sampleItems, {columns}),
      );
      const sortProps = result.current.getSortableSort(2);
      expect(sortProps).toHaveProperty('sortBy');
      expect(sortProps).toHaveProperty('onSort');
      expect(sortProps).toHaveProperty('columnIndex');
      expect(sortProps.columnIndex).toBe(2);
    });

    it('sortBy reflects current sort state', () => {
      const {result} = renderHook(() =>
        usePaginatedSortableTable(sampleItems, {
          columns,
          initialSort: {columnIndex: 0, direction: 'asc'},
        }),
      );
      const sortProps = result.current.getSortableSort(0);
      expect(sortProps.sortBy.index).toBe(0);
      expect(sortProps.sortBy.direction).toBe('asc');
    });
  });

  describe('filtering', () => {
    it('applies filter function to reduce data', () => {
      const {result} = renderHook(() =>
        usePaginatedSortableTable(sampleItems, {
          columns,
          filter: (item) => item.count > 5,
        }),
      );
      expect(result.current.filteredData).toHaveLength(2);
      expect(result.current.paginatedData).toHaveLength(2);
    });

    it('updates totalCount based on filtered data', () => {
      const {result} = renderHook(() =>
        usePaginatedSortableTable(sampleItems, {
          columns,
          filter: (item) => item.name.startsWith('a'),
        }),
      );
      expect(result.current.totalCount).toBe(1);
    });

    it('returns all data when no filter provided', () => {
      const {result} = renderHook(() =>
        usePaginatedSortableTable(sampleItems, {columns}),
      );
      expect(result.current.filteredData).toHaveLength(4);
    });
  });

  describe('filter + sort + paginate pipeline', () => {
    it('filters first, then sorts, then paginates', () => {
      const {result} = renderHook(() =>
        usePaginatedSortableTable(sampleItems, {
          columns,
          filter: (item) => item.count >= 5,
          initialSort: {columnIndex: 1, direction: 'desc'},
          initialPerPage: 2,
        }),
      );
      // Filter: banana(5), apple(10), date(20) — count >= 5
      // Sort desc by count: date(20), apple(10), banana(5)
      // Page 1, perPage 2: [date, apple]
      expect(result.current.filteredData).toHaveLength(3);
      expect(result.current.paginatedData).toHaveLength(2);
      expect(result.current.paginatedData[0].name).toBe('date');
      expect(result.current.paginatedData[1].name).toBe('apple');
    });
  });

  describe('pagination', () => {
    const manyItems = Array.from({length: 25}, (_, i) => ({
      name: `item${String(i).padStart(2, '0')}`,
      count: i,
      hexId: 'aabbccdd',
    }));

    it('returns correct slice for page 1', () => {
      const {result} = renderHook(() =>
        usePaginatedSortableTable(manyItems, {columns, initialPerPage: 10}),
      );
      expect(result.current.paginatedData).toHaveLength(10);
      expect(result.current.paginatedData[0].name).toBe('item00');
    });

    it('returns correct slice for page 2', () => {
      const {result} = renderHook(() =>
        usePaginatedSortableTable(manyItems, {columns, initialPerPage: 10}),
      );
      act(() => {
        result.current.setPage(2);
      });
      expect(result.current.paginatedData).toHaveLength(10);
      expect(result.current.paginatedData[0].name).toBe('item10');
    });

    it('handles partial last page', () => {
      const {result} = renderHook(() =>
        usePaginatedSortableTable(manyItems, {columns, initialPerPage: 10}),
      );
      act(() => {
        result.current.setPage(3);
      });
      expect(result.current.paginatedData).toHaveLength(5);
      expect(result.current.paginatedData[0].name).toBe('item20');
    });

    it('setPage updates current page', () => {
      const {result} = renderHook(() =>
        usePaginatedSortableTable(sampleItems, {columns}),
      );
      act(() => {
        result.current.setPage(2);
      });
      expect(result.current.page).toBe(2);
    });

    it('setPerPage updates items per page', () => {
      const {result} = renderHook(() =>
        usePaginatedSortableTable(manyItems, {columns, initialPerPage: 10}),
      );
      act(() => {
        result.current.setPerPage(5);
      });
      expect(result.current.perPage).toBe(5);
      expect(result.current.paginatedData).toHaveLength(5);
    });
  });

  describe('paginationProps', () => {
    it('returns correct shape', () => {
      const {result} = renderHook(() =>
        usePaginatedSortableTable(sampleItems, {columns}),
      );
      const props = result.current.paginationProps;
      expect(props.total).toBe(4);
      expect(props.itemsList).toHaveLength(4);
      expect(props.perPage).toBe(20);
      expect(props.page).toBe(1);
      expect(typeof props.setPage).toBe('function');
      expect(typeof props.setPerPage).toBe('function');
    });
  });
});
