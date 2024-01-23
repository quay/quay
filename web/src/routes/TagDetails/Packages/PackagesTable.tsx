import {useEffect, useState} from 'react';
import {
  Vulnerability,
  Feature,
  VulnerabilitySeverity,
  VulnerabilityOrder,
} from 'src/resources/TagResource';
import {Table, Thead, Tr, Th, Tbody, Td} from '@patternfly/react-table';
import {
  PageSection,
  PageSectionVariants,
  Spinner,
  Title,
  Toolbar,
  ToolbarContent,
} from '@patternfly/react-core';
import {PackagesFilter} from './PackagesFilter';
import {
  CheckCircleIcon,
  ExclamationTriangleIcon,
} from '@patternfly/react-icons';
import {getSeverityColor} from 'src/libs/utils';
import {VulnerabilityStats} from '../SecurityReport/SecurityReportChart';
import {ToolbarPagination} from 'src/components/toolbar/ToolbarPagination';
import {PackagesListItem} from './Types';

const columnNames = {
  PackageName: 'Package Name',
  PackageVersion: 'Package Version',
  Vulnerabilities: 'Vulnerabilities',
  RemainingAfterUpgrade: 'Remaining After Upgrade',
};

function sortPackages(packagesList: PackagesListItem[]) {
  return packagesList.sort((p1, p2) => {
    if (p1.HighestVulnerabilitySeverity == p2.HighestVulnerabilitySeverity) {
      return (
        VulnerabilityOrder[p1.HighestVulnerabilitySeverityAfterFix] -
        VulnerabilityOrder[p2.HighestVulnerabilitySeverityAfterFix]
      );
    }
    return (
      VulnerabilityOrder[p1.HighestVulnerabilitySeverity] -
      VulnerabilityOrder[p2.HighestVulnerabilitySeverity]
    );
  });
}

function getVulnerabilitiesCount(
  vulnerabilities: Vulnerability[],
  after_fix = false,
): VulnerabilityStats {
  const counts: VulnerabilityStats = {
    [VulnerabilitySeverity.Critical]: 0,
    [VulnerabilitySeverity.High]: 0,
    [VulnerabilitySeverity.Medium]: 0,
    [VulnerabilitySeverity.Low]: 0,
    [VulnerabilitySeverity.Negligible]: 0,
    [VulnerabilitySeverity.Unknown]: 0,
    [VulnerabilitySeverity.None]: 0,
  };

  for (let i = 0; i < vulnerabilities.length; i++) {
    const currentVuln = vulnerabilities[i];
    if (!after_fix || (after_fix && currentVuln.FixedBy == '')) {
      counts[currentVuln.Severity] += 1;
    }
  }
  return counts;
}

function getHighestVulnerabilitySeverity(
  vulnerabilities: Vulnerability[],
  after_fix = false,
) {
  let highestSeverity = VulnerabilitySeverity.Unknown;
  for (let i = 0; i < vulnerabilities.length; i++) {
    const currentVuln = vulnerabilities[i];
    if (!after_fix || (after_fix && currentVuln.FixedBy == '')) {
      if (
        VulnerabilityOrder[currentVuln.Severity] <
        VulnerabilityOrder[highestSeverity]
      ) {
        highestSeverity = currentVuln.Severity;
      }
    }
  }

  return highestSeverity;
}

function TableTitle() {
  return <Title headingLevel={'h1'}> Packages </Title>;
}

function TableHead() {
  return (
    <Thead>
      <Tr>
        <Th>{columnNames.PackageName}</Th>
        <Th>{columnNames.PackageVersion}</Th>
        <Th>{columnNames.Vulnerabilities}</Th>
        <Th>{columnNames.RemainingAfterUpgrade}</Th>
      </Tr>
    </Thead>
  );
}

function VulnerabilitiesEntry(props: VulnerabilitiesEntryProps) {
  if (!props.counts[props.highestSeverity]) {
    return (
      <>
        <CheckCircleIcon color={getSeverityColor(VulnerabilitySeverity.None)} />
        {' None detected'}
      </>
    );
  }

  let total = 0;
  Object.values(props.counts).map((v) => (total += v));

  const remaining = total - props.counts[props.highestSeverity];

  return (
    <>
      <ExclamationTriangleIcon
        color={getSeverityColor(props.highestSeverity)}
      />
      {` ${props.counts[props.highestSeverity]} ${props.highestSeverity}`}
      {remaining > 0 ? ` + ${remaining} Additional` : ''}
    </>
  );
}

export default function PackagesTable({features}: PackagesProps) {
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  const [packagesList, setPackagesList] = useState<PackagesListItem[]>([]);
  const [filteredPackagesList, setFilteredPackagesList] = useState<
    PackagesListItem[]
  >([]);

  // Pagination state
  const [page, setPage] = useState<number>(1);
  const [perPage, setPerPage] = useState<number>(20);
  const paginatedPackagList: PackagesListItem[] = filteredPackagesList.slice(
    (page - 1) * perPage,
    page * perPage,
  );

  useEffect(() => {
    if (features) {
      const packagesList: PackagesListItem[] = [];
      features.map((feature: Feature) => {
        packagesList.push({
          PackageName: feature.Name,
          CurrentVersion: feature.Version,
          Vulnerabilities: feature.Vulnerabilities,

          VulnerabilityCounts: getVulnerabilitiesCount(feature.Vulnerabilities),
          HighestVulnerabilitySeverity: getHighestVulnerabilitySeverity(
            feature.Vulnerabilities,
          ),

          VulnerabilityCountsAfterFix: getVulnerabilitiesCount(
            feature.Vulnerabilities,
            true,
          ),
          HighestVulnerabilitySeverityAfterFix: getHighestVulnerabilitySeverity(
            feature.Vulnerabilities,
            true,
          ),
        } as PackagesListItem);
      });

      const sortedPackagesList = sortPackages(packagesList);
      setPackagesList(sortedPackagesList);
      setFilteredPackagesList(sortedPackagesList);
    } else {
      setPackagesList([]);
      setFilteredPackagesList([]);
    }
  }, [features]);

  return (
    <PageSection variant={PageSectionVariants.light}>
      <TableTitle />
      <Toolbar>
        <ToolbarContent>
          <PackagesFilter
            setPage={setPage}
            packagesList={packagesList}
            setFilteredPackageList={setFilteredPackagesList}
          />
          <ToolbarPagination
            itemsList={filteredPackagesList}
            perPage={perPage}
            page={page}
            setPage={setPage}
            setPerPage={setPerPage}
            id="packages-table-pagination"
          />
        </ToolbarContent>
      </Toolbar>
      <Table
        aria-label="packages table"
        data-testid="packages-table"
        variant="compact"
      >
        <TableHead />
        {paginatedPackagList.length !== 0 ? (
          paginatedPackagList.map((pkg: PackagesListItem) => {
            return (
              <Tbody key={pkg.PackageName + pkg.CurrentVersion}>
                <Tr>
                  <Td dataLabel={columnNames.PackageName}>
                    <span>{pkg.PackageName} </span>
                  </Td>
                  <Td dataLabel={columnNames.PackageVersion}>
                    <span>{pkg.CurrentVersion}</span>
                  </Td>
                  <Td dataLabel={columnNames.Vulnerabilities}>
                    <VulnerabilitiesEntry
                      counts={pkg.VulnerabilityCounts}
                      highestSeverity={pkg.HighestVulnerabilitySeverity}
                    />
                  </Td>
                  <Td dataLabel={columnNames.RemainingAfterUpgrade}>
                    <VulnerabilitiesEntry
                      counts={pkg.VulnerabilityCountsAfterFix}
                      highestSeverity={pkg.HighestVulnerabilitySeverityAfterFix}
                    />
                  </Td>
                </Tr>
              </Tbody>
            );
          })
        ) : (
          <Tbody>
            <Tr>
              <Td>
                {!features ? (
                  <Spinner size="lg" />
                ) : (
                  <div>No Packages Found</div>
                )}
              </Td>
            </Tr>
          </Tbody>
        )}
      </Table>
      <Toolbar>
        <ToolbarPagination
          itemsList={filteredPackagesList}
          perPage={perPage}
          page={page}
          setPage={setPage}
          setPerPage={setPerPage}
        />
      </Toolbar>
    </PageSection>
  );
}

export interface PackagesProps {
  features: Feature[];
}

export interface VulnerabilitiesEntryProps {
  counts: VulnerabilityStats;
  highestSeverity: VulnerabilitySeverity;
}

export interface RemainingAfterUpgradeProps {
  counts: VulnerabilityStats;
  highestSeverity: VulnerabilitySeverity;
}
