import {
  Button,
  Card,
  CardBody,
  CardHeader,
  DescriptionList,
  DescriptionListDescription,
  DescriptionListGroup,
  DescriptionListTerm,
  Divider,
  Flex,
  FlexItem,
  FormSelect,
  FormSelectOption,
  Grid,
  GridItem,
  Label,
  SearchInput,
  Spinner,
  Title,
  Toolbar,
  ToolbarContent,
  ToolbarItem,
} from '@patternfly/react-core';
import {SyncAltIcon} from '@patternfly/react-icons';
import {useEffect, useMemo, useState} from 'react';
import {useFetchDiscoveredRepositories} from 'src/hooks/UseOrgMirror';
import {
  OrgMirrorConfigResponse,
  syncStatusLabels,
} from 'src/resources/OrgMirrorResource';
import DiscoveredReposList from './DiscoveredReposList';

interface SyncStatusDashboardProps {
  organizationName: string;
  mirrorConfig: OrgMirrorConfigResponse;
}

function getSyncStatusColor(
  status: OrgMirrorConfigResponse['sync_status'],
): 'green' | 'red' | 'blue' | 'orange' | 'grey' {
  switch (status) {
    case 'SUCCESS':
      return 'green';
    case 'FAIL':
      return 'red';
    case 'SYNCING':
    case 'SYNC_NOW':
      return 'blue';
    case 'CANCEL':
      return 'orange';
    default:
      return 'grey';
  }
}

const statusFilterOptions = [
  {value: '', label: 'All Statuses'},
  {value: 'DISCOVERED', label: 'Discovered'},
  {value: 'PENDING_SYNC', label: 'Pending Sync'},
  {value: 'CREATED', label: 'Created'},
  {value: 'SKIPPED', label: 'Skipped'},
  {value: 'FAILED', label: 'Failed'},
];

export default function SyncStatusDashboard({
  organizationName,
  mirrorConfig,
}: SyncStatusDashboardProps) {
  const [statusFilter, setStatusFilter] = useState('');
  const [searchTerm, setSearchTerm] = useState('');

  const {discoveredRepos, isLoading, refetch} = useFetchDiscoveredRepositories(
    organizationName,
    statusFilter || undefined,
    true,
  );

  // Filter repos by search term
  const filteredRepos = useMemo(() => {
    if (!discoveredRepos) return [];
    if (!searchTerm.trim()) return discoveredRepos;

    return discoveredRepos.filter(
      (repo) =>
        repo.repository_name.toLowerCase().includes(searchTerm.toLowerCase()) ||
        repo.external_repo_name
          .toLowerCase()
          .includes(searchTerm.toLowerCase()),
    );
  }, [discoveredRepos, searchTerm]);

  // Calculate statistics
  const stats = useMemo(() => {
    if (!discoveredRepos) {
      return {total: 0, created: 0, failed: 0, pending: 0};
    }

    return {
      total: discoveredRepos.length,
      created: discoveredRepos.filter((r) => r.status === 'CREATED').length,
      failed: discoveredRepos.filter((r) => r.status === 'FAILED').length,
      pending: discoveredRepos.filter(
        (r) => r.status === 'DISCOVERED' || r.status === 'PENDING_SYNC',
      ).length,
    };
  }, [discoveredRepos]);

  const handleRefresh = () => {
    refetch();
  };

  const handleStatusFilterChange = (
    _event: React.FormEvent<HTMLSelectElement>,
    value: string,
  ) => {
    setStatusFilter(value);
  };

  const handleSearchChange = (value: string) => {
    setSearchTerm(value);
  };

  const handleSearchClear = () => {
    setSearchTerm('');
  };

  return (
    <>
      <Divider style={{marginTop: '1.5rem', marginBottom: '1.5rem'}} />

      {/* Statistics Cards */}
      <Title headingLevel="h3" style={{marginBottom: '1rem'}}>
        Discovered Repositories
      </Title>

      <Grid hasGutter style={{marginBottom: '1.5rem'}}>
        <GridItem span={3}>
          <Card isCompact data-testid="stat-card-sync-status">
            <CardBody>
              <DescriptionList isHorizontal isCompact>
                <DescriptionListGroup>
                  <DescriptionListTerm>Sync Status</DescriptionListTerm>
                  <DescriptionListDescription>
                    <Label color={getSyncStatusColor(mirrorConfig.sync_status)}>
                      {syncStatusLabels[mirrorConfig.sync_status]}
                    </Label>
                  </DescriptionListDescription>
                </DescriptionListGroup>
              </DescriptionList>
            </CardBody>
          </Card>
        </GridItem>
        <GridItem span={3}>
          <Card isCompact data-testid="stat-card-total">
            <CardBody>
              <DescriptionList isHorizontal isCompact>
                <DescriptionListGroup>
                  <DescriptionListTerm>Total Discovered</DescriptionListTerm>
                  <DescriptionListDescription>
                    <strong>{stats.total}</strong>
                  </DescriptionListDescription>
                </DescriptionListGroup>
              </DescriptionList>
            </CardBody>
          </Card>
        </GridItem>
        <GridItem span={3}>
          <Card isCompact data-testid="stat-card-created">
            <CardBody>
              <DescriptionList isHorizontal isCompact>
                <DescriptionListGroup>
                  <DescriptionListTerm>Created</DescriptionListTerm>
                  <DescriptionListDescription>
                    <Label color="green">{stats.created}</Label>
                  </DescriptionListDescription>
                </DescriptionListGroup>
              </DescriptionList>
            </CardBody>
          </Card>
        </GridItem>
        <GridItem span={3}>
          <Card isCompact data-testid="stat-card-failed">
            <CardBody>
              <DescriptionList isHorizontal isCompact>
                <DescriptionListGroup>
                  <DescriptionListTerm>Failed</DescriptionListTerm>
                  <DescriptionListDescription>
                    <Label color={stats.failed > 0 ? 'red' : 'grey'}>
                      {stats.failed}
                    </Label>
                  </DescriptionListDescription>
                </DescriptionListGroup>
              </DescriptionList>
            </CardBody>
          </Card>
        </GridItem>
      </Grid>

      {/* Toolbar with search and filters */}
      <Toolbar>
        <ToolbarContent>
          <ToolbarItem variant="search-filter">
            <SearchInput
              placeholder="Search repositories..."
              value={searchTerm}
              onChange={(_event, value) => handleSearchChange(value)}
              onClear={handleSearchClear}
              data-testid="repo-search-input"
            />
          </ToolbarItem>
          <ToolbarItem>
            <FormSelect
              value={statusFilter}
              onChange={handleStatusFilterChange}
              aria-label="Filter by status"
              data-testid="status-filter-select"
            >
              {statusFilterOptions.map((option) => (
                <FormSelectOption
                  key={option.value}
                  value={option.value}
                  label={option.label}
                />
              ))}
            </FormSelect>
          </ToolbarItem>
          <ToolbarItem>
            <Button
              variant="secondary"
              icon={<SyncAltIcon />}
              onClick={handleRefresh}
              isLoading={isLoading}
              data-testid="refresh-repos-btn"
            >
              Refresh
            </Button>
          </ToolbarItem>
        </ToolbarContent>
      </Toolbar>

      {/* Discovered Repos List */}
      {isLoading ? (
        <Flex
          justifyContent={{default: 'justifyContentCenter'}}
          style={{padding: '2rem'}}
        >
          <FlexItem>
            <Spinner size="lg" />
          </FlexItem>
        </Flex>
      ) : (
        <DiscoveredReposList
          repos={filteredRepos}
          organizationName={organizationName}
          isLoading={isLoading}
        />
      )}
    </>
  );
}
