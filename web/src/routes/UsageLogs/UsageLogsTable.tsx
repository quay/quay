import {
  Button,
  Flex,
  FlexItem,
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
import {useState} from 'react';

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

export function UsageLogsTable(props: UsageLogsTableProps) {
  const logDescriptions = useLogDescriptions();

  const [filterValue, setFilterValue] = useState('');

  const filterOnChange = (value: string) => {
    setFilterValue(value);
  };

  const filterLogs = (data: LogPage, filterValue: string): LogPage => {
    data.logs = data.logs.filter(function (log) {
      return log.kind.includes(filterValue);
    });
    return data;
  };

  const queryClient = useQueryClient();

  const {
    data: logs,
    isLoading: loadingLogs,
    isError: errorLogs,
    fetchNextPage,
    hasNextPage,
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
    select: (data) => {
      data.pages = data.pages.map((logs) => filterLogs(logs, filterValue));
      return data;
    },
    retry: props.isSuperuser && props.freshLogin ? false : true, // Don't auto-retry when fresh login is available
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
          <Table variant="compact" borders={false} style={{margin: '20px'}}>
            <Thead>
              <Tr>
                <Th width={15}>Date & Time</Th>
                <Th>Description</Th>
                {props.isSuperuser && <Th>Namespace</Th>}
                {!props.repo && <Th>Repository</Th>}
                <Th>Performed by</Th>
                <Th>IP Address</Th>
              </Tr>
            </Thead>
            <Tbody>
              {logs.pages.map((logPage: LogPage) =>
                logPage.logs.map((log: LogEntry, index: number) => (
                  <Tr key={index}>
                    <Td>
                      <TableText wrapModifier="truncate">
                        {new Date(log.datetime).toLocaleString()}
                      </TableText>
                    </Td>
                    <Td>
                      {logDescriptions[log.kind]
                        ? logDescriptions[log.kind](log.metadata)
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
                      {log.performer?.name ||
                        log.metadata?.performer ||
                        '(anonymous)'}
                    </Td>
                    <Td>{log.ip}</Td>
                  </Tr>
                )),
              )}
            </Tbody>
          </Table>
        </FlexItem>
        <FlexItem align={{default: 'alignRight'}}>
          <Button
            variant="secondary"
            onClick={() => {
              fetchNextPage();
            }}
            isDisabled={!hasNextPage}
          >
            Load More Logs
          </Button>
        </FlexItem>
      </Flex>
    </>
  );
}
