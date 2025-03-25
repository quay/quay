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
import {useInfiniteQuery} from '@tanstack/react-query';
import RequestError from 'src/components/errors/RequestError';
import {getLogs} from 'src/hooks/UseUsageLogs';
import {useLogDescriptions} from 'src/hooks/UseLogDescriptions';
import {useEffect, useState} from 'react';

interface UsageLogsTableProps {
  starttime: string;
  endtime: string;
  org: string;
  repo: string;
  type: string;
}

export function UsageLogsTable(props: UsageLogsTableProps) {
  const logDescriptions = useLogDescriptions();

  const [filterValue, setFilterValue] = useState('');

  const filterOnChange = (value: string) => {
    setFilterValue(value);
  };

  const filterLogs = (data, filterValue) => {
    data.logs = data.logs.filter(function (log) {
      return log.kind.includes(filterValue);
    });
    return data;
  };

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
    getNextPageParam: (lastPage: {[key: string]: string}) => lastPage.nextPage,
    select: (data) => {
      data.pages = data.pages.map((logs) => filterLogs(logs, filterValue));
      return data;
    },
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
                <Th>Performed by</Th>
                <Th>IP Address</Th>
              </Tr>
            </Thead>
            <Tbody>
              {logs.pages.map((logPage: any) =>
                logPage.logs.map((log: any, index: number) => (
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
                    <Td>
                      {log.performer?.name
                        ? log.performer?.name
                        : log.metadata?.performer}
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
