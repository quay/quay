import {
  Flex,
  FlexItem,
  PanelFooter,
  Spinner,
  SearchInput,
  Split,
  SplitItem,
} from '@patternfly/react-core';
import {
  Table,
  Tbody,
  Td,
  Th,
  Thead,
  Tr,
  TableText,
} from '../../components/QuayTable';
import {useInfiniteQuery} from '@tanstack/react-query';
import RequestError from 'src/components/errors/RequestError';
import {getLogs} from 'src/hooks/UseUsageLogs';
import {useLogDescriptions} from 'src/hooks/UseLogDescriptions';
import {usePaginatedSortableTable} from '../../hooks/usePaginatedSortableTable';
import {ToolbarPagination} from 'src/components/toolbar/ToolbarPagination';
import {useState, useMemo} from 'react';

interface UsageLogsTableProps {
  starttime: string;
  endtime: string;
  org: string;
  repo: string;
  type: string;
}

interface LogEntry {
  datetime: string;
  kind: string;
  metadata?: Record<string, unknown>;
  performer?: {
    name: string;
  };
  ip: string;
}

interface LogPage {
  logs: LogEntry[];
  nextPage?: string;
}

export function UsageLogsTable(props: UsageLogsTableProps) {
  const logDescriptions = useLogDescriptions();

  const [filterValue, setFilterValue] = useState('');

  const filterOnChange = (value: string) => {
    setFilterValue(value);
  };

  const filterLogs = (data: LogPage, filterValue: string): LogPage => {
    data.logs = data.logs.filter(function (log: LogEntry) {
      return log.kind.includes(filterValue);
    });
    return data;
  };

  const {
    data: logs,
    isLoading: loadingLogs,
    isError: errorLogs,
  } = useInfiniteQuery({
    queryKey: [
      'usageLogs',
      props.starttime,
      props.endtime,
      {org: props.org, repo: props.repo ? props.repo : 'isOrg', type: 'table'},
    ],
    queryFn: async ({pageParam = undefined}) => {
      const logResp = await getLogs(
        props.org,
        props.repo,
        props.starttime,
        props.endtime,
        pageParam,
      );
      return logResp;
    },
    getNextPageParam: (lastPage: LogPage) => lastPage.nextPage,
    select: (data) => {
      data.pages = data.pages.map((logs: LogPage) =>
        filterLogs(logs, filterValue),
      );
      return data;
    },
  });

  // Flatten all log pages into a single array for our table hook
  const flattenedLogs: LogEntry[] = useMemo(() => {
    if (!logs?.pages) return [];
    return logs.pages.flatMap((page: LogPage) => page.logs);
  }, [logs]);

  // Create filter function for the table hook
  const searchFilter = useMemo(() => {
    if (!filterValue) return undefined;
    return (log: LogEntry) => log.kind.includes(filterValue);
  }, [filterValue]);

  // Use unified table hook for sorting and pagination
  const {
    paginatedData: paginatedLogs,
    getSortableSort,
    paginationProps,
  } = usePaginatedSortableTable(flattenedLogs, {
    columns: {
      0: (log: LogEntry) => new Date(log.datetime).getTime(), // Date & Time (sort by timestamp)
      1: (log: LogEntry) => (logDescriptions[log.kind] ? log.kind : 'zzz'), // Description (sort by kind)
      2: (log: LogEntry) =>
        log.performer?.name || (log.metadata?.performer as string) || '', // Performed by
      3: (log: LogEntry) => log.ip || '', // IP Address
    },
    filter: searchFilter,
    initialPerPage: 20,
    initialSort: {columnIndex: 0, direction: 'desc'}, // Default sort: newest first
  });

  if (loadingLogs) return <Spinner />;
  if (errorLogs) return <RequestError message="Unable to retrieve logs" />;

  return (
    <>
      <Flex direction={{default: 'column'}} style={{margin: '20px'}}>
        <FlexItem>
          <Split>
            <SplitItem isFilled />
            <SplitItem>
              <SearchInput
                placeholder="Filter logs"
                value={filterValue}
                onChange={(_event, value) => filterOnChange(value)}
                onClear={() => filterOnChange('')}
                id="log-filter-input"
              />
            </SplitItem>
          </Split>
        </FlexItem>
        <FlexItem>
          <div style={{margin: '20px'}}>
            <Table variant="compact" aria-label="Usage logs table">
              <Thead>
                <Tr>
                  <Th width={15} sort={getSortableSort(0)}>
                    Date & Time
                  </Th>
                  <Th sort={getSortableSort(1)}>Description</Th>
                  <Th sort={getSortableSort(2)}>Performed by</Th>
                  <Th sort={getSortableSort(3)}>IP Address</Th>
                </Tr>
              </Thead>
              <Tbody>
                {paginatedLogs.map((log: LogEntry, index: number) => (
                  <Tr key={`${log.datetime}-${index}`}>
                    <Td>
                      <TableText wrapModifier="truncate">
                        {new Date(log.datetime).toLocaleString()}
                      </TableText>
                    </Td>
                    <Td>
                      {logDescriptions[log.kind]
                        ? (logDescriptions[log.kind](
                            log.metadata,
                          ) as React.ReactNode)
                        : 'No description available'}
                    </Td>
                    <Td>
                      {log.performer?.name
                        ? log.performer?.name
                        : (log.metadata?.performer as string) || 'Unknown'}
                    </Td>
                    <Td>{log.ip}</Td>
                  </Tr>
                ))}
              </Tbody>
            </Table>
          </div>
        </FlexItem>
        <PanelFooter>
          <ToolbarPagination {...paginationProps} bottom={true} />
        </PanelFooter>
      </Flex>
    </>
  );
}
