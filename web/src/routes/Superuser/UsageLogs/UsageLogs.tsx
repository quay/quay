import {
  PageSection,
  PageSectionVariants,
  Title,
  Button,
  DatePicker,
  Flex,
  FlexItem,
  Split,
  SplitItem,
} from '@patternfly/react-core';
import {QuayBreadcrumb} from 'src/components/breadcrumb/Breadcrumb';
import {useCurrentUser} from 'src/hooks/UseCurrentUser';
import {Navigate} from 'react-router-dom';
import UsageLogsGraph from '../../UsageLogs/UsageLogsGraph';
import {UsageLogsTable} from '../../UsageLogs/UsageLogsTable';
import React from 'react';

function UsageLogsHeader() {
  return (
    <>
      <QuayBreadcrumb />
      <PageSection variant={PageSectionVariants.light} hasShadowBottom>
        <div className="co-m-nav-title--row">
          <Title headingLevel="h1">Usage Logs</Title>
        </div>
      </PageSection>
    </>
  );
}

function formatDate(date: string) {
  /**
   * change date string from y-m-d to m%d%y for api
   */
  const dates = date.split('-');
  const year = dates[0];
  const month = dates[1];
  const day = dates[2];

  return `${month}/${day}/${year}`;
}

export default function UsageLogs() {
  const {isSuperUser, loading} = useCurrentUser();

  // Date state and logic
  const maxDate = new Date();
  const minDate = new Date();
  minDate.setMonth(maxDate.getMonth() - 1);
  minDate.setDate(minDate.getDate() + 1);

  const [logStartDate, setLogStartDate] = React.useState<string>(
    formatDate(minDate.toISOString().split('T')[0]),
  );
  const [logEndDate, setLogEndDate] = React.useState<string>(
    formatDate(maxDate.toISOString().split('T')[0]),
  );

  const [chartHidden, setChartHidden] = React.useState<boolean>(false);

  // Helper to parse date string back to Date object for comparison
  const parseFormattedDate = (dateStr: string): Date => {
    const [month, day, year] = dateStr.split('/');
    return new Date(parseInt(year), parseInt(month) - 1, parseInt(day));
  };

  const startDateValidator = (date: Date): string => {
    if (date < minDate) {
      return 'Logs are only available for the past month';
    } else if (date > maxDate) {
      return 'Cannot select future dates';
    }

    // Check if start date is after end date
    const endDate = parseFormattedDate(logEndDate);
    if (date > endDate) {
      return 'From date cannot be after To date';
    }

    return '';
  };

  const endDateValidator = (date: Date): string => {
    if (date < minDate) {
      return 'Logs are only available for the past month';
    } else if (date > maxDate) {
      return 'Cannot select future dates';
    }

    // Check if end date is before start date
    const startDate = parseFormattedDate(logStartDate);
    if (date < startDate) {
      return 'To date cannot be before From date';
    }

    return '';
  };

  if (loading) {
    return null;
  }

  // Redirect non-superusers
  if (!isSuperUser) {
    return <Navigate to="/repository" replace />;
  }

  return (
    <>
      <UsageLogsHeader />
      <PageSection>
        <Flex direction={{default: 'column'}}>
          <FlexItem>
            <Split hasGutter style={{marginBottom: '20px'}}>
              <SplitItem>
                <Button
                  variant="secondary"
                  onClick={() => setChartHidden(!chartHidden)}
                >
                  {chartHidden ? 'Show Chart' : 'Hide Chart'}
                </Button>
              </SplitItem>
              <SplitItem isFilled></SplitItem>
              <SplitItem>
                <strong style={{marginRight: '10px'}}>From:</strong>
                <DatePicker
                  value={logStartDate}
                  onChange={(_event, str) => {
                    setLogStartDate(formatDate(str));
                  }}
                  validators={[startDateValidator]}
                />
              </SplitItem>
              <SplitItem>
                <strong style={{marginRight: '10px'}}>To:</strong>
                <DatePicker
                  value={logEndDate}
                  onChange={(_event, str) => {
                    setLogEndDate(formatDate(str));
                  }}
                  validators={[endDateValidator]}
                />
              </SplitItem>
            </Split>
          </FlexItem>
          <FlexItem>
            {chartHidden ? null : (
              <UsageLogsGraph
                starttime={logStartDate}
                endtime={logEndDate}
                repo=""
                org=""
                type="superuser"
                isSuperuser={true}
              />
            )}
          </FlexItem>
          <FlexItem>
            <UsageLogsTable
              starttime={logStartDate}
              endtime={logEndDate}
              repo=""
              org=""
              type="superuser"
              isSuperuser={true}
            />
          </FlexItem>
        </Flex>
      </PageSection>
    </>
  );
}
