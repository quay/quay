import {
  Chart,
  ChartAxis,
  ChartBar,
  ChartLegend,
  ChartGroup,
  ChartVoronoiContainer,
} from '@patternfly/react-charts';
import {getAggregateLogs} from 'src/hooks/UseUsageLogs';

import {useQuery, useQueryClient} from '@tanstack/react-query';
import RequestError from 'src/components/errors/RequestError';
import {Flex, FlexItem, Spinner} from '@patternfly/react-core';
import {logKinds} from './UsageLogs';

import './css/UsageLogs.scss';

interface UsageLogsGraphProps {
  starttime: string;
  endtime: string;
  repo: string;
  org: string;
  type: string;
  isSuperuser?: boolean;
  freshLogin?: {
    showFreshLoginModal: (retryOperation: () => Promise<void>) => void;
    isFreshLoginRequired: (error: unknown) => boolean;
  };
}

export default function UsageLogsGraph(props: UsageLogsGraphProps) {
  const queryClient = useQueryClient();

  const {
    data: aggregateLogs,
    isError: errorFetchingLogs,
    isLoading: loadingAggregateLogs,
  } = useQuery(
    [
      'usageLogs',
      props.starttime,
      props.endtime,
      {
        org: props.org,
        repo: props.repo ? props.repo : 'isOrg',
        type: 'chart',
        isSuperuser: props.isSuperuser,
      },
    ],
    async () => {
      try {
        return await getAggregateLogs(
          props.org,
          props.repo,
          props.starttime,
          props.endtime,
          props.isSuperuser,
        );
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
                  type: 'chart',
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
    {
      retry: props.isSuperuser && props.freshLogin ? false : true, // Don't auto-retry when fresh login is available
    },
  );

  // tslint:disable-next-line:curly
  if (loadingAggregateLogs) return <Spinner />;
  // tslint:disable-next-line:curly
  if (errorFetchingLogs) return <RequestError message="Unable to get logs" />;

  let maxRange = 0;

  function createDataSet() {
    const logData = {};
    if (aggregateLogs) {
      aggregateLogs.forEach((log) => {
        logData[log.kind] = logData[log.kind] || [];
        logData[log.kind].push({
          name: logKinds[log.kind],
          x: new Date(log.datetime),
          y: log.count,
        });
        // tslint:disable-next-line:curly
        if (log.count > maxRange) maxRange = log.count;
      });
      return logData;
    }
  }

  const logData = createDataSet();

  function getLegendData() {
    const legends = [];
    const logKeys = Object.keys(logData);
    logKeys.forEach((key) => {
      if (logKinds[key]) {
        legends.push({name: logKinds[key]});
      }
    });
    return legends;
  }

  if (getLegendData().length === 0) {
    return (
      <Flex grow={{default: 'grow'}} style={{margin: '50px'}}>
        <FlexItem>
          <p>No data to display.</p>
        </FlexItem>
      </Flex>
    );
    // tslint:disable-next-line:curly
  } else
    return (
      <Flex grow={{default: 'grow'}}>
        <FlexItem>
          <Chart
            key={props.starttime + props.endtime}
            containerComponent={
              <ChartVoronoiContainer
                labels={({datum}) => `${datum.name}: ${datum.y}`}
                constrainToVisibleArea
              />
            }
            domain={{
              x: [new Date(props.starttime), new Date(props.endtime)],
              y: [0, maxRange],
            }}
            legendAllowWrap
            legendComponent={
              <ChartLegend data={getLegendData()} itemsPerRow={8} />
            }
            legendPosition="right"
            legendOrientation={
              getLegendData().length >= 12 ? 'horizontal' : 'vertical'
            }
            name="usage-logs-graph"
            padding={{
              bottom: 50,
              left: 80,
              right: 500, // Adjusted to accommodate legend
              top: 50,
            }}
            domainPadding={{x: 5 * Object.keys(logData).length}}
            height={400}
            width={1250}
            scale={{x: 'time', y: 'linear'}}
          >
            <ChartAxis fixLabelOverlap />
            <ChartAxis dependentAxis showGrid />
            <ChartGroup offset={11}>
              {Object.keys(logData).map((logKind, index) => (
                <ChartBar data={logData[logKind]} key={index} />
              ))}
            </ChartGroup>
          </Chart>
        </FlexItem>
      </Flex>
    );
}
