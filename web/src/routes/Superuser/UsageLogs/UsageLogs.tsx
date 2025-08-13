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
import {useFreshLogin} from 'src/hooks/UseFreshLogin';
import {FreshLoginModal} from 'src/components/modals/FreshLoginModal';
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
  const freshLogin = useFreshLogin();

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

  const rangeValidator = (date: Date): string => {
    if (date > maxDate) {
      return 'Cannot select future dates';
    }
    return '';
  };

  if (loading) {
    return null;
  }

  // Redirect non-superusers
  if (!isSuperUser) {
    return <Navigate to="/organization" replace />;
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
                  validators={[rangeValidator]}
                />
              </SplitItem>
              <SplitItem>
                <strong style={{marginRight: '10px'}}>To:</strong>
                <DatePicker
                  value={logEndDate}
                  onChange={(_event, str) => {
                    setLogEndDate(formatDate(str));
                  }}
                  validators={[rangeValidator]}
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
                freshLogin={{
                  showFreshLoginModal: freshLogin.showFreshLoginModal,
                  isFreshLoginRequired: freshLogin.isFreshLoginRequired,
                }}
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
              freshLogin={{
                showFreshLoginModal: freshLogin.showFreshLoginModal,
                isFreshLoginRequired: freshLogin.isFreshLoginRequired,
              }}
            />
          </FlexItem>
        </Flex>
      </PageSection>

      <FreshLoginModal
        isOpen={freshLogin.isModalOpen}
        onCancel={freshLogin.handleCancel}
        onVerify={freshLogin.handleVerify}
        isLoading={freshLogin.isLoading}
        error={freshLogin.error}
      />
    </>
  );
}
