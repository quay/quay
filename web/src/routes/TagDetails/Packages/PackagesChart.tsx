import { ChartDonut } from '@patternfly/react-charts';
import {
  PageSection,
  PageSectionVariants,
  Skeleton,
  Split,
  SplitItem,
  Title,
  TitleSizes,
} from '@patternfly/react-core';
import { BundleIcon } from '@patternfly/react-icons';
import { Feature, VulnerabilitySeverity } from 'src/resources/TagResource';
import { getSeverityColor } from 'src/libs/utils';
import { VulnerabilityStats } from '../SecurityReport/SecurityReportChart';
import { useQuayConfig } from 'src/hooks/UseQuayConfig';

function PackageMessage(props: PackageMessageProps) {
  if (props.vulnLevel === 'None') {
    return <> Packages with no vulnerabilities</>;
  }
  return <> Packages with {props.vulnLevel}-level vulnerabilities</>;
}

function PackagesSummary(props: PackageStatsProps) {
  let packagesMessage = <Skeleton width="400px" />;
  let availableMessage = <Skeleton width="300px" />;

  // Check if API call has completed and if packages are found
  if (props.stats[VulnerabilitySeverity.None] > 0 && props.total === 0) {
    packagesMessage = (
      <> Quay Security Reporting does not recognize any packages </>
    );
    availableMessage = <> No known patches are available </>;
  } else if (props.total > 0) {
    packagesMessage = (
      <> Quay Security Reporting has recognized {props.total} packages </>
    );
    availableMessage = (
      <> Patches are available for {props.patchesAvailable} vulnerabilities </>
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
          {packagesMessage}
        </Title>
        <Title headingLevel="h3" className="pf-v5-u-mb-lg">
          {availableMessage}
        </Title>

        {Object.keys(props.stats).map((vulnLevel) => {
          if (props.stats[vulnLevel] > 0) {
            return;
            {
              props.stats.Pending === 0 ? (
                <div className="pf-v5-u-mb-sm" key={vulnLevel}>
                  <BundleIcon
                    color={getSeverityColor(vulnLevel as VulnerabilitySeverity)}
                    className="pf-v5-u-mr-md"
                  />
                  <b>{props.stats[vulnLevel]}</b>
                  <PackageMessage vulnLevel={vulnLevel} />
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

function PackagesDonutChart(props: PackageStatsProps) {
  return (
    <div style={{ height: '20em', width: '20em' }}>
      {props.stats.Pending > 0 ? (
        <Skeleton shape="circle" width="100%" />
      ) : (
        <ChartDonut
          ariaDesc="packages chart"
          ariaTitle="packages chart"
          constrainToVisibleArea={true}
          data={[
            { x: VulnerabilitySeverity.Critical, y: props.stats.Critical },
            { x: VulnerabilitySeverity.High, y: props.stats.High },
            { x: VulnerabilitySeverity.Medium, y: props.stats.Medium },
            { x: VulnerabilitySeverity.Unknown, y: props.stats.Unknown },
            { x: VulnerabilitySeverity.None, y: props.stats.None },
            { x: VulnerabilitySeverity.Suppressed, y: props.suppressed },
          ]}
          colorScale={[
            getSeverityColor(VulnerabilitySeverity.Critical),
            getSeverityColor(VulnerabilitySeverity.High),
            getSeverityColor(VulnerabilitySeverity.Medium),
            getSeverityColor(VulnerabilitySeverity.Unknown),
            getSeverityColor(VulnerabilitySeverity.None),
            getSeverityColor(VulnerabilitySeverity.Suppressed),
          ]}
          labels={({ datum }) => `${datum.x}: ${datum.y}`}
          title={`${props.total}`}
          style={{
            data: { stroke: ({ datum }) => datum.x === `${VulnerabilitySeverity.Suppressed}` ? "#ccc" : null },
          }}
        />
      )}
    </div>
  );
}

export function PackagesChart(props: PackageChartProps) {
  const config = useQuayConfig();
  const stats = {
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
  let totalPackages = 0;
  let totalPackagesPerSeverity = 0;
  let totalSuppressed = 0;

  if (props.features) {
    if (props.features.length > 0) {
      props.features.map((feature) => {
        totalPackages += 1;
        const perPackageVulnStats = {
          Critical: 0,
          High: 0,
          Medium: 0,
          Low: 0,
          Negligible: 0,
          Unknown: 0,
          Suppressed: 0,
        };

        feature.Vulnerabilities.map((vulnerability) => {
          if (config?.features.SECURITY_VULNERABILITY_SUPPRESSION && 'SuppressedBy' in vulnerability) {
            if (vulnerability.SuppressedBy.length > 0) {
              perPackageVulnStats[perPackageVulnStats.Suppressed] = 1;
            }
          } else {
            perPackageVulnStats[vulnerability.Severity] = 1;
          }

          if (vulnerability.FixedBy.length > 0) {
            patchesAvailable += 1;
          }
        });


        // add perPackageStats to totals
        Object.keys(perPackageVulnStats).map((severity) => {
          if (severity === 'Suppressed') {
            totalSuppressed += perPackageVulnStats[severity];
          } else {
            stats[severity] += perPackageVulnStats[severity];
          }

          if (perPackageVulnStats[severity] > 0) {
              totalPackagesPerSeverity += 1;
            }
        });

        if (feature.Vulnerabilities.length == 0) {
          stats[VulnerabilitySeverity.None] += 1;
          totalPackagesPerSeverity += 1;
        }
      });
    } else {
      // No packages found
      stats[VulnerabilitySeverity.None] += 1;
    }
  } else {
    // Waiting on API call to finish
    stats.Pending = 1;
  }

  return (
    <PageSection variant={PageSectionVariants.light}>
      <Split>
        <SplitItem data-testid="packages-chart">
          <PackagesDonutChart
            stats={stats}
            total={totalPackagesPerSeverity}
            patchesAvailable={patchesAvailable}
            suppressed={totalSuppressed}
          />
        </SplitItem>
        <SplitItem>
          <PackagesSummary
            stats={stats}
            total={totalPackages}
            patchesAvailable={patchesAvailable}
            suppressed={totalSuppressed}
          />
        </SplitItem>
      </Split>
    </PageSection>
  );
}

interface PackageStatsProps {
  stats: VulnerabilityStats;
  total: number;
  patchesAvailable: number;
  suppressed: number;
}

interface PackageChartProps {
  features: Feature[];
}

interface PackageMessageProps {
  vulnLevel: string;
}
