import React, {useState, useMemo, useCallback} from 'react';
import {
  Bullseye,
  Card,
  CardBody,
  EmptyState,
  EmptyStateBody,
  EmptyStateHeader,
  EmptyStateIcon,
  Pagination,
  PaginationVariant,
  SearchInput,
  Text,
  TextContent,
  TextVariants,
  Toolbar,
  ToolbarContent,
  ToolbarItem,
} from '@patternfly/react-core';
import {SearchIcon} from '@patternfly/react-icons';
import {
  Table,
  Thead,
  Tbody,
  Tr,
  Th,
  Td,
  ThProps,
} from '@patternfly/react-table';
import billOfMaterials from '../../bill-of-materials.json';

interface BillOfMaterialsEntry {
  project: string;
  license: string;
  format: string;
}

type SortableColumn = 'project' | 'license' | 'format';

export const PackagesTable: React.FC = () => {
  const [searchValue, setSearchValue] = useState<string>('');
  const [page, setPage] = useState<number>(1);
  const [perPage, setPerPage] = useState<number>(20);
  const [activeSortIndex, setActiveSortIndex] = useState<number>(0);
  const [activeSortDirection, setActiveSortDirection] = useState<
    'asc' | 'desc'
  >('asc');

  const columnNames: {key: SortableColumn; label: string}[] = [
    {key: 'project', label: 'PROJECT NAME'},
    {key: 'license', label: 'PROJECT LICENSE'},
    {key: 'format', label: 'TYPE'},
  ];

  // Filter data based on search
  const filteredData = useMemo(() => {
    const data = billOfMaterials as BillOfMaterialsEntry[];
    if (!searchValue) {
      return data;
    }
    const lowerSearch = searchValue.toLowerCase();
    return data.filter((entry) => {
      return (
        entry.project.toLowerCase().includes(lowerSearch) ||
        entry.license.toLowerCase().includes(lowerSearch) ||
        entry.format.toLowerCase().includes(lowerSearch)
      );
    });
  }, [searchValue]);

  // Sort data
  const sortedData = useMemo(() => {
    const sortKey = columnNames[activeSortIndex].key;
    return [...filteredData].sort((a, b) => {
      const aValue = a[sortKey];
      const bValue = b[sortKey];

      if (activeSortDirection === 'asc') {
        return aValue.localeCompare(bValue);
      } else {
        return bValue.localeCompare(aValue);
      }
    });
  }, [filteredData, activeSortIndex, activeSortDirection]);

  // Paginate data
  const paginatedData = useMemo(() => {
    const startIndex = (page - 1) * perPage;
    const endIndex = startIndex + perPage;
    return sortedData.slice(startIndex, endIndex);
  }, [sortedData, page, perPage]);

  const getSortParams = useCallback(
    (columnIndex: number): ThProps['sort'] => {
      return {
        sortBy: {
          index: activeSortIndex,
          direction: activeSortDirection,
          defaultDirection: 'asc',
        },
        onSort: (_event, index, direction) => {
          setActiveSortIndex(index);
          setActiveSortDirection(direction);
        },
        columnIndex,
      };
    },
    [activeSortIndex, activeSortDirection],
  );

  const handleSearchChange = useCallback(
    (_event: React.FormEvent<HTMLInputElement>, value: string) => {
      setSearchValue(value);
      setPage(1); // Reset to first page on search
    },
    [],
  );

  const handleClearSearch = useCallback(() => {
    setSearchValue('');
    setPage(1);
  }, []);

  const handleSetPage = useCallback(
    (
      _event: React.MouseEvent | React.KeyboardEvent | MouseEvent,
      newPage: number,
    ) => {
      setPage(newPage);
    },
    [],
  );

  const handlePerPageSelect = useCallback(
    (
      _event: React.MouseEvent | React.KeyboardEvent | MouseEvent,
      newPerPage: number,
      newPage: number,
    ) => {
      setPerPage(newPerPage);
      setPage(newPage);
    },
    [],
  );

  return (
    <>
      <TextContent style={{marginBottom: '1rem', marginTop: '2rem'}}>
        <Text component={TextVariants.h2}>Packages and Projects used</Text>
      </TextContent>
      <Card>
        <CardBody>
          <Toolbar>
            <ToolbarContent>
              <ToolbarItem variant="search-filter">
                <SearchInput
                  placeholder="Search packages..."
                  value={searchValue}
                  onChange={handleSearchChange}
                  onClear={handleClearSearch}
                  aria-label="Search packages"
                />
              </ToolbarItem>
              <ToolbarItem
                variant="pagination"
                alignment={{default: 'alignRight'}}
              >
                <Pagination
                  itemCount={filteredData.length}
                  perPage={perPage}
                  page={page}
                  onSetPage={handleSetPage}
                  onPerPageSelect={handlePerPageSelect}
                  variant={PaginationVariant.top}
                  isCompact
                />
              </ToolbarItem>
            </ToolbarContent>
          </Toolbar>
          <Table aria-label="Packages and projects table" variant="compact">
            <Thead>
              <Tr>
                <Th sort={getSortParams(0)}>{columnNames[0].label}</Th>
                <Th sort={getSortParams(1)}>{columnNames[1].label}</Th>
                <Th sort={getSortParams(2)}>{columnNames[2].label}</Th>
              </Tr>
            </Thead>
            <Tbody>
              {paginatedData.length > 0 ? (
                paginatedData.map((entry, index) => (
                  <Tr key={`${entry.project}-${index}`}>
                    <Td dataLabel={columnNames[0].label}>{entry.project}</Td>
                    <Td dataLabel={columnNames[1].label}>{entry.license}</Td>
                    <Td dataLabel={columnNames[2].label}>{entry.format}</Td>
                  </Tr>
                ))
              ) : (
                <Tr>
                  <Td colSpan={3}>
                    <Bullseye>
                      <EmptyState variant="sm">
                        <EmptyStateHeader
                          titleText="No results found"
                          icon={<EmptyStateIcon icon={SearchIcon} />}
                          headingLevel="h2"
                        />
                        <EmptyStateBody>
                          No packages match your search criteria. Clear the
                          search to show all packages.
                        </EmptyStateBody>
                      </EmptyState>
                    </Bullseye>
                  </Td>
                </Tr>
              )}
            </Tbody>
          </Table>
          <Toolbar>
            <ToolbarContent>
              <ToolbarItem
                variant="pagination"
                alignment={{default: 'alignRight'}}
              >
                <Pagination
                  itemCount={filteredData.length}
                  perPage={perPage}
                  page={page}
                  onSetPage={handleSetPage}
                  onPerPageSelect={handlePerPageSelect}
                  variant={PaginationVariant.bottom}
                />
              </ToolbarItem>
            </ToolbarContent>
          </Toolbar>
        </CardBody>
      </Card>
    </>
  );
};

export default PackagesTable;
