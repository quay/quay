import {Button, Flex, FlexItem, Spinner} from '@patternfly/react-core';
import {Table, Tbody, Td, Th, Thead, Tr} from '@patternfly/react-table';
import {useInfiniteQuery} from '@tanstack/react-query';
import RequestError from 'src/components/errors/RequestError';
import {getLogs} from 'src/hooks/UseUsageLogs';
import {useLogDescriptions} from 'src/hooks/UseLogDescriptions';

interface UsageLogsTableProps {
  starttime: string;
  endtime: string;
  org: string;
  repo: string;
  type: string;
}

export function UsageLogsTable(props: UsageLogsTableProps) {
  const logDescriptions = useLogDescriptions();
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
  });

  if (loadingLogs) return <Spinner />;
  if (errorLogs) return <RequestError message="Unable to retrieve logs" />;

  return (
    <>
      <Flex direction={{default: 'column'}} style={{margin: '20px'}}>
        <FlexItem>
          <Table variant="compact" borders={false} style={{margin: '20px'}}>
            <Thead>
              <Tr>
                <Th>Date & Time</Th>
                <Th>Description</Th>
                <Th>Performed by</Th>
                <Th>IP address</Th>
              </Tr>
            </Thead>
            <Tbody>
              {logs.pages.map((logPage: any) =>
                logPage.logs.map((log: any, index: number) => (
                  <Tr key={index}>
                    <Td>{new Date(log.datetime).toLocaleString()}</Td>
                    <Td>
                      {logDescriptions[log.kind]
                        ? logDescriptions[log.kind](log.metadata)
                        : 'No description available'}
                    </Td>
                    <Td>{log.performer?.name}</Td>
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
