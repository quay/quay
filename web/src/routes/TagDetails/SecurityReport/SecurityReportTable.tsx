import {useEffect, useState} from 'react';
import {Vulnerability, Feature} from 'src/resources/TagResource';
import React from 'react';
import {
  ExpandableRowContent,
  Table,
  Tbody,
  Td,
  Th,
  Thead,
  Tr,
} from '@patternfly/react-table';
import {usePaginatedSortableTable} from '../../../hooks/usePaginatedSortableTable';
import {SecurityReportMetadataTable} from './SecurityReportMetadataTable';
import {
  PageSection,
  PageSectionVariants,
  Spinner,
  Title,
  Toolbar,
  ToolbarContent,
} from '@patternfly/react-core';
import {SecurityReportFilter} from './SecurityReportFilter';
import sha1 from 'js-sha1';
import {
  ArrowRightIcon,
  ExclamationTriangleIcon,
  ExternalLinkAltIcon,
} from '@patternfly/react-icons';
import {getSeverityColor} from 'src/libs/utils';

import './SecurityReportTable.css';
import {ToolbarPagination} from 'src/components/toolbar/ToolbarPagination';
import {VulnerabilityListItem} from './Types';

const columnNames = {
  advisory: 'Advisory',
  severity: 'Severity',
  package: 'Package',
  currentVersion: 'Current Version',
  fixedInVersion: 'Fixed in Version',
};

const VulnSeverityOrder = {
  Critical: 0,
  High: 1,
  Medium: 2,
  Low: 3,
  Unknown: 4,
};

function getVulnerabilityLink(vulnerability: VulnerabilityListItem) {
  if (!vulnerability.Link) {
    return '';
  }

  // by default return the first link
  return vulnerability.Link.split(' ')[0];
}

function TableTitle() {
  return <Title headingLevel={'h1'}> Advisories </Title>;
}

export default function SecurityReportTable({features}: SecurityDetailsProps) {
  const [vulnList, setVulnList] = useState<VulnerabilityListItem[]>([]);
  const [expandedVulnKeys, setExpandedVulnKeys] = React.useState<string[]>([]);

  // Filter state
  const [searchTerm, setSearchTerm] = useState<string>('');
  const [isFixedOnlyChecked, setIsFixedOnlyChecked] = useState<boolean>(false);

  // Combined filter function for search term and fixable-only
  const searchFilter = (vuln: VulnerabilityListItem) => {
    const searchStr = vuln.PackageName + vuln.Advisory;
    const matchesSearch = searchStr
      .toLowerCase()
      .includes(searchTerm.toLowerCase());
    const matchesFixable = !isFixedOnlyChecked || Boolean(vuln.FixedInVersion);
    return matchesSearch && matchesFixable;
  };

  // Use unified table hook for sorting, filtering, and pagination
  const {
    paginatedData: paginatedVulns,
    getSortableSort,
    paginationProps,
  } = usePaginatedSortableTable(vulnList, {
    columns: {
      0: (vuln: VulnerabilityListItem) => vuln.Advisory, // Advisory
      1: (vuln: VulnerabilityListItem) =>
        VulnSeverityOrder[vuln.Severity] || 999, // Severity (preserve custom order)
      2: (vuln: VulnerabilityListItem) => vuln.PackageName, // Package
      3: (vuln: VulnerabilityListItem) => vuln.CurrentVersion, // Current Version
      4: (vuln: VulnerabilityListItem) => vuln.FixedInVersion || 'zzz', // Fixed in Version (null values sort to end)
    },
    initialSort: {columnIndex: 1, direction: 'asc'}, // Default sort: Severity (asc = Critical first because Critical=0, High=1, etc.)
    initialPerPage: 20,
    filter: searchFilter,
  });

  function TableHead() {
    return (
      <Thead>
        <Tr>
          <Th />
          <Th sort={getSortableSort(0)}>{columnNames.advisory}</Th>
          <Th sort={getSortableSort(1)} id="severity-sort">
            {columnNames.severity}
          </Th>
          <Th sort={getSortableSort(2)}>{columnNames.package}</Th>
          <Th sort={getSortableSort(3)}>{columnNames.currentVersion}</Th>
          <Th sort={getSortableSort(4)}>{columnNames.fixedInVersion}</Th>
        </Tr>
      </Thead>
    );
  }

  const generateUniqueKey = (vulnerability: VulnerabilityListItem) => {
    let hashInput =
      vulnerability.PackageName +
      vulnerability.Advisory +
      vulnerability.Description +
      vulnerability.Severity;

    if (vulnerability.Metadata) {
      hashInput += vulnerability.Metadata.RepoName;
    }

    return sha1(hashInput);
  };

  const setRepoExpanded = (key: string, isExpanding = true) =>
    setExpandedVulnKeys((prevExpanded) => {
      const otherExpandedKeys = prevExpanded.filter((k) => k !== key);
      return isExpanding ? [...otherExpandedKeys, key] : otherExpandedKeys;
    });

  const isRepoExpanded = (key: string) => expandedVulnKeys.includes(key);

  useEffect(() => {
    if (features) {
      const vulnListData: VulnerabilityListItem[] = [];
      features.map((feature: Feature) => {
        feature.Vulnerabilities.map((vulnerability: Vulnerability) => {
          vulnListData.push({
            PackageName: feature.Name,
            CurrentVersion: feature.Version,
            Description: vulnerability.Description,
            NamespaceName: vulnerability.NamespaceName,
            Advisory: vulnerability.Name,
            Severity: vulnerability.Severity,
            FixedInVersion: vulnerability.FixedBy,
            Metadata: vulnerability.Metadata,
            Link: vulnerability.Link,
          } as VulnerabilityListItem);
        });
      });
      setVulnList(vulnListData);
    } else {
      setVulnList([]);
    }
  }, [features]);

  return (
    <PageSection variant={PageSectionVariants.light}>
      <TableTitle />
      <Toolbar>
        <ToolbarContent>
          <SecurityReportFilter
            setPage={paginationProps.setPage}
            vulnList={vulnList}
            searchTerm={searchTerm}
            setSearchTerm={setSearchTerm}
            isFixedOnlyChecked={isFixedOnlyChecked}
            setIsFixedOnlyChecked={setIsFixedOnlyChecked}
          />
          <ToolbarPagination {...paginationProps} />
        </ToolbarContent>
      </Toolbar>
      <Table
        data-testid="vulnerability-table"
        aria-label="Expandable table"
        variant="compact"
      >
        <TableHead />
        {paginatedVulns.length !== 0 ? (
          paginatedVulns.map(
            (vulnerability: VulnerabilityListItem, rowIndex) => {
              const uniqueKey = generateUniqueKey(vulnerability);
              return (
                <Tbody key={uniqueKey} isExpanded={isRepoExpanded(uniqueKey)}>
                  <Tr className="security-table-row">
                    <Td
                      expand={{
                        rowIndex,
                        isExpanded: isRepoExpanded(uniqueKey),
                        onToggle: () =>
                          setRepoExpanded(
                            uniqueKey,
                            !isRepoExpanded(uniqueKey),
                          ),
                      }}
                    />

                    <Td dataLabel={columnNames.advisory}>
                      <>
                        {vulnerability.Advisory}
                        {vulnerability.Link ? (
                          <a
                            href={getVulnerabilityLink(vulnerability)}
                            target="_blank"
                            rel="noreferrer"
                          >
                            <ExternalLinkAltIcon style={{marginLeft: '5px'}} />
                          </a>
                        ) : null}
                      </>
                    </Td>
                    <Td dataLabel={columnNames.severity}>
                      <ExclamationTriangleIcon
                        color={getSeverityColor(vulnerability.Severity)}
                        style={{
                          marginRight: '5px',
                        }}
                      />
                      <span>{vulnerability.Severity}</span>
                    </Td>
                    <Td dataLabel={columnNames.package}>
                      {vulnerability.PackageName}
                    </Td>
                    <Td dataLabel={columnNames.currentVersion}>
                      {vulnerability.CurrentVersion}
                    </Td>
                    <Td dataLabel={columnNames.fixedInVersion}>
                      {vulnerability.FixedInVersion ? (
                        <>
                          <ArrowRightIcon
                            color={'green'}
                            style={{marginRight: '5px'}}
                          />
                          <span>{vulnerability.FixedInVersion}</span>
                        </>
                      ) : (
                        '(None)'
                      )}
                    </Td>
                  </Tr>

                  <Tr isExpanded={isRepoExpanded(uniqueKey)}>
                    <Td
                      dataLabel="Security Metadata"
                      colSpan={5}
                      cellPadding="span"
                    >
                      <ExpandableRowContent>
                        <SecurityReportMetadataTable
                          vulnerability={vulnerability}
                        />
                      </ExpandableRowContent>
                    </Td>
                  </Tr>
                </Tbody>
              );
            },
          )
        ) : (
          <Tbody>
            <Tr>
              <Td>
                {!features ? (
                  <Spinner size="lg" />
                ) : (
                  <div>No Vulnerabilities Found</div>
                )}
              </Td>
            </Tr>
          </Tbody>
        )}
      </Table>
    </PageSection>
  );
}

export interface SecurityDetailsProps {
  features: Feature[];
}
