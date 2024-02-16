import {
  Chart,
  ChartAxis,
  ChartBar,
  ChartGroup,
  ChartVoronoiContainer,
} from '@patternfly/react-charts';
import {getAggregateLogs} from 'src/hooks/UseUsageLogs';

import {useQuery} from '@tanstack/react-query';
import RequestError from 'src/components/errors/RequestError';
import {Flex, FlexItem, Spinner} from '@patternfly/react-core';
import {logDescriptions} from './UsageLogs';

interface UsageLogsGraphProps {
  starttime: string;
  endtime: string;
  repo: string;
  org: string;
  type: string;
}

export default function UsageLogsGraph(props: UsageLogsGraphProps) {
  const {
    data: aggregateLogs,
    isError: errorFetchingLogs,
    isLoading: loadingAggregateLogs,
  } = useQuery(['aggregateLogs', props.org, props.repo], () => {
    return getAggregateLogs(
      props.org,
      props.repo,
      props.starttime,
      props.endtime,
    );
  });

  if (loadingAggregateLogs) return <Spinner />;
  if (errorFetchingLogs) return <RequestError message="Unable to get logs" />;

  let maxRange = 0;

  function createDataSet() {
    const logData = {};
    if (aggregateLogs) {
      aggregateLogs.forEach((log) => {
        logData[log.kind] = logData[log.kind] || [];
        logData[log.kind].push({
          name: logDescriptions[log.kind],
          x: new Date(log.datetime),
          y: log.count,
        });
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
      if (logDescriptions[key]) {
        legends.push({name: logDescriptions[key]});
      }
    });
    return legends;
  }

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
          legendOrientation="vertical"
          legendPosition="right"
          legendData={getLegendData()}
          legendAllowWrap
          name="usage-logs-graph"
          padding={{
            bottom: 50,
            left: 80,
            right: 500, // Adjusted to accommodate legend
            top: 50,
          }}
          height={400}
          width={1250}
          domainPadding={{x: 40}}
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
