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
import {useQuayConfig} from 'src/hooks/UseQuayConfig';
import {getSeverityColor} from 'src/libs/utils';
import {
  Feature,
  VulnerabilitySeverity,
  VulnerabilitySuppressionSource,
} from 'src/resources/TagResource';
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

  let suppressionMessage = <Skeleton width="300px" />;
  let suppressionMessageString = '';

  const suppressionSources = [];
  if (props.suppressed === 0) {
    suppressionMessage = <> </>;
  } else {
    if (props.suppressionStats.Repository > 0) {
      suppressionSources.push('repository');
    }
    if (props.suppressionStats.Organization > 0) {
      suppressionSources.push('organization');
    }
    if (props.suppressionStats.Manifest > 0) {
      suppressionSources.push('manifest');
    }

    if (props.suppressed === 1) {
      suppressionMessageString = `${props.suppressed} vulnerability is suppressed by the `;
    } else {
      suppressionMessageString = `${props.suppressed} vulnerabilities are suppressed by the `;
    }

    const suppressionSourcesString = suppressionSources.join(', ');
    const suppressionSourcesStringWithAnd = suppressionSourcesString.replace(
      /,([^,]*)$/,
      ' and$1',
    );
    suppressionMessage = (
      <>
        {suppressionMessageString} {suppressionSourcesStringWithAnd} settings{' '}
      </>
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
          <br />
          {suppressionMessage}
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
            {x: VulnerabilitySeverity.Suppressed, y: props.suppressed},
          ]}
          colorScale={[
            getSeverityColor(VulnerabilitySeverity.Critical),
            getSeverityColor(VulnerabilitySeverity.High),
            getSeverityColor(VulnerabilitySeverity.Medium),
            getSeverityColor(VulnerabilitySeverity.Low),
            getSeverityColor(VulnerabilitySeverity.Negligible),
            getSeverityColor(VulnerabilitySeverity.Unknown),
            getSeverityColor(VulnerabilitySeverity.None),
            getSeverityColor(VulnerabilitySeverity.Suppressed),
          ]}
          labels={({datum}) => `${datum.x}: ${datum.y}`}
          title={`${props.total}`}
          style={{
            data: {
              stroke: ({datum}) =>
                datum.x === `${VulnerabilitySeverity.Suppressed}`
                  ? '#ccc'
                  : null,
            },
          }}
        />
      )}
    </div>
  );
}

export function SecurityReportChart(props: SecurityDetailsChartProps) {
  const config = useQuayConfig();
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

  const suppressionStats: VulnerabilitySuppressionStats = {
    Manifest: 0,
    Organization: 0,
    Repository: 0,
  };

  let suppressed = 0;
  let patchesAvailable = 0;
  let total = 0;

  // Count vulnerabilities if API call has completed
  if (props.features) {
    props.features.map((feature) => {
      feature.Vulnerabilities.map((vulnerability) => {
        if (
          config?.features.SECURITY_VULNERABILITY_SUPPRESSION &&
          'SuppressedBy' in vulnerability
        ) {
          suppressed += 1;

          switch (vulnerability.SuppressedBy) {
            case VulnerabilitySuppressionSource.Manifest:
              suppressionStats.Manifest += 1;
              break;
            case VulnerabilitySuppressionSource.Organization:
              suppressionStats.Organization += 1;
              break;
            case VulnerabilitySuppressionSource.Repository:
              suppressionStats.Repository += 1;
              break;
          }
        } else {
          stats[vulnerability.Severity] += 1;
          total += 1;
        }

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
            suppressed={suppressed}
            suppressionStats={suppressionStats}
            setIsOpen={props.setIsOpen}
          />
        </SplitItem>
        <SplitItem>
          <VulnerabilitySummary
            stats={stats}
            total={total}
            patchesAvailable={patchesAvailable}
            suppressed={suppressed}
            suppressionStats={suppressionStats}
            setIsOpen={props.setIsOpen}
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

export interface VulnerabilitySuppressionStats {
  Manifest: number;
  Organization: number;
  Repository: number;
}

interface VulnerabilityStatsProps {
  stats: VulnerabilityStats;
  total: number;
  patchesAvailable: number;
  suppressed: number;
  suppressionStats: VulnerabilitySuppressionStats;
  setIsOpen: (isOpen: boolean) => void;
}

interface SecurityDetailsChartProps {
  setIsOpen: (isOpen: boolean) => void;
  features: Feature[];
}
