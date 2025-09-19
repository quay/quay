import {useEffect, useState} from 'react';
import {
  Vulnerability,
  Feature,
  VulnerabilitySeverity,
  VulnerabilityOrder,
} from 'src/resources/TagResource';
import {
  Table,
  Tbody,
  Td,
  Th,
  ThProps,
  Thead,
  Tr,
} from '@patternfly/react-table';
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
import {usePaginatedSortableTable} from '../../../hooks/usePaginatedSortableTable';

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
    Pending: 0,
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

function TableHead({
  getSortableSort,
}: {
  getSortableSort: (columnIndex: number) => ThProps['sort'];
}) {
  return (
    <Thead>
      <Tr>
        <Th sort={getSortableSort(0)}>{columnNames.PackageName}</Th>
        <Th sort={getSortableSort(1)}>{columnNames.PackageVersion}</Th>
        <Th sort={getSortableSort(2)}>{columnNames.Vulnerabilities}</Th>
        <Th sort={getSortableSort(3)}>{columnNames.RemainingAfterUpgrade}</Th>
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

  // Use our sortable table hook for sorting and pagination
  const {
    paginatedData: paginatedPackageList,
    getSortableSort,
    paginationProps,
  } = usePaginatedSortableTable(filteredPackagesList || [], {
    columns: {
      0: (item: PackagesListItem) => item.PackageName, // Package Name
      1: (item: PackagesListItem) => item.CurrentVersion, // Package Version
      2: (item: PackagesListItem) =>
        VulnerabilityOrder[item.HighestVulnerabilitySeverity], // Vulnerabilities (by severity order)
      3: (item: PackagesListItem) =>
        VulnerabilityOrder[item.HighestVulnerabilitySeverityAfterFix], // Remaining After Upgrade (by severity order)
    },
    initialPerPage: 20,
    initialSort: {columnIndex: 2, direction: 'asc'}, // Default sort: Vulnerabilities by severity (most severe first)
  });

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
            setPage={paginationProps.setPage}
            packagesList={packagesList}
            setFilteredPackageList={setFilteredPackagesList}
          />
          <ToolbarPagination
            itemsList={filteredPackagesList}
            perPage={paginationProps.perPage}
            page={paginationProps.page}
            setPage={paginationProps.setPage}
            setPerPage={paginationProps.setPerPage}
            id="packages-table-pagination"
          />
        </ToolbarContent>
      </Toolbar>
      <Table
        aria-label="packages table"
        data-testid="packages-table"
        variant="compact"
      >
        <TableHead getSortableSort={getSortableSort} />
        {paginatedPackageList.length !== 0 ? (
          paginatedPackageList.map((pkg: PackagesListItem) => {
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
          perPage={paginationProps.perPage}
          page={paginationProps.page}
          setPage={paginationProps.setPage}
          setPerPage={paginationProps.setPerPage}
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
