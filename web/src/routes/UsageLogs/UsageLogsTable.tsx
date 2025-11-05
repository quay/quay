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
  TableText,
  Tbody,
  Td,
  Th,
  Thead,
  Tr,
} from '@patternfly/react-table';
import {useInfiniteQuery, useQueryClient} from '@tanstack/react-query';
import RequestError from 'src/components/errors/RequestError';
import {getLogs} from 'src/hooks/UseUsageLogs';
import {useLogDescriptions} from 'src/hooks/UseLogDescriptions';
import {usePaginatedSortableTable} from '../../hooks/usePaginatedSortableTable';
import {ToolbarPagination} from 'src/components/toolbar/ToolbarPagination';
import {extractTextFromReactNode} from 'src/libs/utils';
import {useState, useMemo} from 'react';

interface LogEntry {
  datetime: string;
  kind: string;
  metadata: {
    [key: string]: string;
    namespace?: string;
    repo?: string;
    performer?: string;
  };
  namespace?: {
    name?: string;
    username?: string;
  };
  performer?: {
    name?: string;
  };
  ip: string;
}

interface LogPage {
  logs: LogEntry[];
  nextPage?: string;
}

interface UsageLogsTableProps {
  starttime: string;
  endtime: string;
  org: string;
  repo: string;
  type: string;
  isSuperuser?: boolean;
  freshLogin?: {
    showFreshLoginModal: (retryOperation: () => Promise<void>) => void;
    isFreshLoginRequired: (error: unknown) => boolean;
  };
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

  const queryClient = useQueryClient();

  const {
    data: logs,
    isLoading: loadingLogs,
    isError: errorLogs,
  } = useInfiniteQuery({
    queryKey: [
      'usageLogs',
      props.starttime,
      props.endtime,
      {
        org: props.org,
        repo: props.repo ? props.repo : 'isOrg',
        type: 'table',
        isSuperuser: props.isSuperuser,
      },
    ],
    queryFn: async ({pageParam = undefined}) => {
      try {
        const logResp = await getLogs(
          props.org,
          props.repo,
          props.starttime,
          props.endtime,
          pageParam,
          props.isSuperuser,
        );
        return logResp;
      } catch (error: unknown) {
        // Check if this is a fresh login required error and we have fresh login integration
        if (
          props.isSuperuser &&
          props.freshLogin?.isFreshLoginRequired(error)
        ) {
          // Show fresh login modal with retry operation
          props.freshLogin.showFreshLoginModal(async () => {
            // Retry the query after successful verification
            queryClient.invalidateQueries({
              queryKey: [
                'usageLogs',
                props.starttime,
                props.endtime,
                {
                  org: props.org,
                  repo: props.repo ? props.repo : 'isOrg',
                  type: 'table',
                  isSuperuser: props.isSuperuser,
                },
              ],
            });
          });

          // Don't throw the error - the modal will handle retry
          throw new Error('Fresh login required');
        }
        throw error;
      }
    },
    getNextPageParam: (lastPage: LogPage) => lastPage.nextPage,
    retry: props.isSuperuser && props.freshLogin ? false : true, // Don't auto-retry when fresh login is available
  });

  // Flatten all log pages into a single array for our table hook
  const flattenedLogs: LogEntry[] = useMemo(() => {
    if (!logs?.pages) return [];
    return logs.pages.flatMap((page: LogPage) => page.logs);
  }, [logs]);

  // Create filter function for the table hook
  const searchFilter = useMemo(() => {
    if (!filterValue) return undefined;
    const searchTerm = filterValue.toLowerCase();
    return (log: LogEntry) => {
      // Search across multiple fields for better filtering
      const namespace = log.namespace?.name || log.namespace?.username || '';
      const repo = log.metadata?.repo
        ? `${log.metadata?.namespace || ''}/${log.metadata.repo}`
        : '';
      const performer =
        log.performer?.name || (log.metadata?.performer as string) || '';
      const ip = log.ip || '';
      const kind = log.kind || '';

      // Get the description text if available
      // Use extractTextFromReactNode to convert JSX elements to searchable plain text
      const description = logDescriptions[log.kind]
        ? typeof logDescriptions[log.kind] === 'function'
          ? extractTextFromReactNode(logDescriptions[log.kind](log.metadata))
          : extractTextFromReactNode(logDescriptions[log.kind])
        : '';

      // Check if any field contains the search term (case-insensitive)
      return (
        namespace.toLowerCase().includes(searchTerm) ||
        repo.toLowerCase().includes(searchTerm) ||
        performer.toLowerCase().includes(searchTerm) ||
        ip.toLowerCase().includes(searchTerm) ||
        kind.toLowerCase().includes(searchTerm) ||
        description.toLowerCase().includes(searchTerm)
      );
    };
  }, [filterValue, logDescriptions]);

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
                  {props.isSuperuser && <Th>Namespace</Th>}
                  {!props.repo && <Th>Repository</Th>}
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
                    {props.isSuperuser && (
                      <Td>
                        {log.namespace?.name || log.namespace?.username || ''}
                      </Td>
                    )}
                    {!props.repo && (
                      <Td>
                        {log.metadata?.namespace && log.metadata?.repo
                          ? `${log.metadata.namespace}/${log.metadata.repo}`
                          : log.metadata?.repo || ''}
                      </Td>
                    )}
                    <Td>
                      {log.performer?.name
                        ? log.performer?.name
                        : (log.metadata?.performer as string) || '(anonymous)'}
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
