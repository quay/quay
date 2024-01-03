import {ChartDonut} from '@patternfly/react-charts';
import {
  PageSection,
  PageSectionVariants,
  Skeleton,
  Split,
  SplitItem,
  Title,
  TitleSizes,
} from '@patternfly/react-core';
import {ExclamationTriangleIcon} from '@patternfly/react-icons';
import {getSeverityColor} from 'src/libs/utils';
import {Feature, VulnerabilitySeverity} from 'src/resources/TagResource';
import './SecurityReportChart.css';

function VulnerabilitySummary(props: VulnerabilityStatsProps) {
  let message = <Skeleton width="400px" />;
  if (props.stats[VulnerabilitySeverity.None] > 0) {
    message = <> Quay Security Reporting has detected no vulnerabilities </>;
  } else if (props.total > 0) {
    message = (
      <> Quay Security Reporting has detected {props.total} vulnerabilities </>
    );
  }

  let patchesMessage = <Skeleton width="300px" />;
  if (props.stats[VulnerabilitySeverity.None] > 0) {
    patchesMessage = <> </>;
  } else if (props.total > 0) {
    patchesMessage = (
      <> Patches are available for {props.patchesAvailable} vulnerabilities</>
    );
  }

  return (
    <div>
      <div className="pf-v5-u-mt-xl pf-v5-u-ml-2xl">
        <Title
          headingLevel="h1"
          size={TitleSizes['3xl']}
          className="pf-v5-u-mb-sm"
        >
          {message}
        </Title>
        <Title headingLevel="h3" className="pf-v5-u-mb-lg">
          {patchesMessage}
        </Title>
        {Object.keys(props.stats).map((vulnLevel) => {
          if (
            props.stats[vulnLevel] > 0 &&
            vulnLevel != VulnerabilitySeverity.None
          ) {
            return;
            {
              props.stats.Pending === 0 ? (
                <div className="pf-v5-u-mb-sm" key={vulnLevel}>
                  <ExclamationTriangleIcon
                    color={getSeverityColor(vulnLevel as VulnerabilitySeverity)}
                    className="pf-v5-u-mr-md"
                  />
                  <b>{props.stats[vulnLevel]}</b> {vulnLevel}-level
                  vulnerabilities
                </div>
              ) : (
                <div></div>
              );
            }
          }
        })}
      </div>
    </div>
  );
}

function VulnerabilityChart(props: VulnerabilityStatsProps) {
  return (
    <div style={{height: '20em', width: '20em'}}>
      {props.stats.Pending > 0 ? (
        <Skeleton shape="circle" width="100%" />
      ) : (
        <ChartDonut
          ariaDesc="vulnerability chart"
          ariaTitle="vulnerability chart"
          constrainToVisibleArea={true}
          data={[
            {x: VulnerabilitySeverity.Critical, y: props.stats.Critical},
            {x: VulnerabilitySeverity.High, y: props.stats.High},
            {x: VulnerabilitySeverity.Medium, y: props.stats.Medium},
            {x: VulnerabilitySeverity.Low, y: props.stats.Low},
            {x: VulnerabilitySeverity.Negligible, y: props.stats.Negligible},
            {x: VulnerabilitySeverity.Unknown, y: props.stats.Unknown},
            {x: VulnerabilitySeverity.None, y: props.stats.None},
          ]}
          colorScale={[
            getSeverityColor(VulnerabilitySeverity.Critical),
            getSeverityColor(VulnerabilitySeverity.High),
            getSeverityColor(VulnerabilitySeverity.Medium),
            getSeverityColor(VulnerabilitySeverity.Low),
            getSeverityColor(VulnerabilitySeverity.Negligible),
            getSeverityColor(VulnerabilitySeverity.Unknown),
            getSeverityColor(VulnerabilitySeverity.None),
          ]}
          labels={({datum}) => `${datum.x}: ${datum.y}`}
          title={`${props.total}`}
        />
      )}
    </div>
  );
}

export function SecurityReportChart(props: SecurityDetailsChartProps) {
  const stats: VulnerabilityStats = {
    Critical: 0,
    High: 0,
    Medium: 0,
    Low: 0,
    Negligible: 0,
    Unknown: 0,
    None: 0,
    Pending: 0,
  };

  let patchesAvailable = 0;
  let total = 0;

  // Count vulnerabilities if API call has completed
  if (props.features) {
    props.features.map((feature) => {
      feature.Vulnerabilities.map((vulnerability) => {
        stats[vulnerability.Severity] += 1;
        total += 1;
        if (vulnerability.FixedBy.length > 0) {
          patchesAvailable += 1;
        }
      });
    });

    // No vulnerabilities
    if (total == 0) {
      stats[VulnerabilitySeverity.None] = 1;
    }
  } else {
    // Waiting on API call to finish
    stats.Pending = 1;
  }

  return (
    <PageSection variant={PageSectionVariants.light}>
      <Split>
        <SplitItem data-testid="vulnerability-chart">
          <VulnerabilityChart
            stats={stats}
            total={total}
            patchesAvailable={patchesAvailable}
          />
        </SplitItem>
        <SplitItem>
          <VulnerabilitySummary
            stats={stats}
            total={total}
            patchesAvailable={patchesAvailable}
          />
        </SplitItem>
      </Split>
    </PageSection>
  );
}

export interface VulnerabilityStats {
  Critical: number;
  High: number;
  Medium: number;
  Low: number;
  Negligible: number;
  Unknown: number;
  None: number;
  Pending: number;
}

interface VulnerabilityStatsProps {
  stats: VulnerabilityStats;
  total: number;
  patchesAvailable: number;
}

interface SecurityDetailsChartProps {
  features: Feature[];
}
