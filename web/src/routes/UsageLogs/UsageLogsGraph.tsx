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

  // D3 Category20 colors (same as Angular)
  const d3Category20Colors = [
    '#1f77b4',
    '#aec7e8',
    '#ff7f0e',
    '#ffbb78',
    '#2ca02c',
    '#98df8a',
    '#d62728',
    '#ff9896',
    '#9467bd',
    '#c5b0d5',
    '#8c564b',
    '#c49c94',
    '#e377c2',
    '#f7b6d2',
    '#7f7f7f',
    '#c7c7c7',
    '#bcbd22',
    '#dbdb8d',
    '#17becf',
    '#9edae5',
  ];

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
        if (logKinds[log.kind]) {
          logData[log.kind] = logData[log.kind] || [];
          logData[log.kind].push({
            name: logKinds[log.kind],
            x: new Date(log.datetime),
            y: log.count,
          });
          if (log.count > maxRange) maxRange = log.count;
        }
      });
      return logData;
    }
  }

  const logData = createDataSet();

  function getLegendData() {
    const legends = [];
    const logKeys = Object.keys(logData);

    logKeys.forEach((key, index) => {
      if (logKinds[key]) {
        legends.push({
          name: logKinds[key],
          symbol: {
            fill: d3Category20Colors[index % d3Category20Colors.length],
            type: 'square',
          },
        });
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
              <ChartLegend
                data={getLegendData()}
                itemsPerRow={6}
                style={{
                  labels: {fontSize: 11},
                }}
              />
            }
            // @ts-expect-error PatternFly's type definitions are incomplete, but "top" works in practice
            legendPosition="top"
            legendOrientation="horizontal"
            name="usage-logs-graph"
            padding={{
              bottom: 50,
              left: 80,
              right: 50,
              top: 120, // More space for legend above chart
            }}
            domainPadding={{x: 5 * Object.keys(logData).length}}
            height={500}
            width={1200}
            scale={{x: 'time', y: 'linear'}}
          >
            <ChartAxis fixLabelOverlap />
            <ChartAxis dependentAxis showGrid />
            <ChartGroup offset={11}>
              {Object.keys(logData).map((logKind, index) => (
                <ChartBar
                  data={logData[logKind]}
                  key={index}
                  style={{
                    data: {
                      fill: d3Category20Colors[
                        index % d3Category20Colors.length
                      ],
                    },
                  }}
                />
              ))}
            </ChartGroup>
          </Chart>
        </FlexItem>
      </Flex>
    );
}
