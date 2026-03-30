import React, {useState} from 'react';
import {
  Divider,
  Title,
  Label,
  MenuToggle,
  Pagination,
  Select,
  SelectList,
  SelectOption,
  Spinner,
  Content,
  Toolbar,
  ToolbarContent,
  ToolbarItem,
  Tooltip,
} from '@patternfly/react-core';
import {ExclamationTriangleIcon} from '@patternfly/react-icons';
import {Table, Thead, Tr, Th, Tbody, Td} from '@patternfly/react-table';
import {useQuery} from '@tanstack/react-query';
import {
  OrgMirrorConfig,
  OrgMirrorReposResponse,
  getOrgMirrorRepos,
  orgMirrorStatusLabels,
  orgMirrorStatusColors,
} from 'src/resources/OrgMirrorResource';
import {formatDate} from 'src/libs/utils';
import {Link} from 'react-router-dom';

interface OrgMirroringReposProps {
  config: OrgMirrorConfig | null;
  orgName: string;
  isOrgSyncing: boolean;
}

// Repo-level statuses reuse the org-level maps, with one extra display-only status
const repoStatusColors: Record<
  string,
  'blue' | 'green' | 'red' | 'cyan' | 'orange' | 'grey'
> = {
  ...orgMirrorStatusColors,
  DISCOVERED: 'grey',
};

const repoStatusLabels: Record<string, string> = {
  ...orgMirrorStatusLabels,
  DISCOVERED: 'Discovered',
};

// Filterable statuses — derived from repo-level label map for consistency
const filterableStatuses: {value: string; label: string}[] = [
  'NEVER_RUN',
  'SYNC_NOW',
  'SYNCING',
  'SUCCESS',
  'FAIL',
  'CANCEL',
  'SKIP',
].map((value) => ({
  value,
  label: repoStatusLabels[value] ?? value,
}));

export const OrgMirroringRepos: React.FC<OrgMirroringReposProps> = ({
  config,
  orgName,
  isOrgSyncing,
}) => {
  const [page, setPage] = useState(1);
  const [perPage, setPerPage] = useState(20);
  const [statusFilter, setStatusFilter] = useState<string>('');
  const [isFilterOpen, setIsFilterOpen] = useState(false);

  const {
    data,
    isLoading,
    error: queryError,
  } = useQuery<OrgMirrorReposResponse>({
    queryKey: ['org-mirror-repos', orgName, page, perPage, statusFilter],
    queryFn: () =>
      getOrgMirrorRepos(orgName, page, perPage, statusFilter || undefined),
    enabled: !!config,
    refetchInterval: isOrgSyncing ? 5000 : false,
  });

  const repos = data?.repositories ?? [];
  const total = data?.total ?? 0;
  const error = queryError
    ? (queryError as Error).message || 'Failed to load discovered repositories'
    : null;

  if (!config) {
    return null;
  }

  return (
    <>
      <Divider />
      <Title headingLevel="h3">Discovered Repositories</Title>

      {isLoading && <Spinner size="md" />}

      {error && (
        <Content component="p" className="pf-v6-u-danger-color-100">
          {error}
        </Content>
      )}

      {!isLoading && !error && repos.length === 0 && !statusFilter && (
        <Content component="p">
          No repositories discovered yet. Repositories will appear here after
          the first sync.
        </Content>
      )}

      {!isLoading && !error && repos.length === 0 && statusFilter && (
        <Content component="p">
          No repositories match the selected status filter.
        </Content>
      )}

      {!isLoading && !error && (total > 0 || statusFilter) && (
        <Toolbar>
          <ToolbarContent>
            <ToolbarItem>
              <Select
                isOpen={isFilterOpen}
                onOpenChange={setIsFilterOpen}
                onSelect={(_event, value) => {
                  setStatusFilter(value as string);
                  setIsFilterOpen(false);
                  setPage(1);
                }}
                toggle={(toggleRef) => (
                  <MenuToggle
                    ref={toggleRef}
                    onClick={() => setIsFilterOpen(!isFilterOpen)}
                    isExpanded={isFilterOpen}
                    data-testid="status-filter-toggle"
                  >
                    {statusFilter
                      ? repoStatusLabels[statusFilter] || statusFilter
                      : 'All statuses'}
                  </MenuToggle>
                )}
                selected={statusFilter}
              >
                <SelectList>
                  <SelectOption value="" data-testid="status-filter-all">
                    All statuses
                  </SelectOption>
                  {filterableStatuses.map(({value, label}) => (
                    <SelectOption
                      key={value}
                      value={value}
                      data-testid={`status-filter-${value}`}
                    >
                      {label}
                    </SelectOption>
                  ))}
                </SelectList>
              </Select>
            </ToolbarItem>
          </ToolbarContent>
        </Toolbar>
      )}

      {!isLoading && !error && repos.length > 0 && (
        <>
          <Table
            aria-label="Discovered repositories"
            variant="compact"
            data-testid="org-mirror-repos-table"
          >
            <Thead>
              <Tr>
                <Th>Repository Name</Th>
                <Th>Sync Status</Th>
                <Th>Discovery Date</Th>
                <Th>Last Sync</Th>
                <Th>Quay Repository</Th>
              </Tr>
            </Thead>
            <Tbody>
              {repos.map((repo) => (
                <Tr key={repo.name}>
                  <Td dataLabel="Repository Name">{repo.name}</Td>
                  <Td dataLabel="Sync Status">
                    <Label color={repoStatusColors[repo.sync_status] || 'grey'}>
                      {repoStatusLabels[repo.sync_status] || repo.sync_status}
                    </Label>
                    {repo.status_message && (
                      <Tooltip content={repo.status_message}>
                        <button
                          type="button"
                          aria-label={repo.status_message}
                          data-testid={`status-warning-${repo.name}`}
                          className="pf-v6-u-ml-sm"
                          style={{
                            background: 'none',
                            border: 'none',
                            padding: 0,
                            cursor: 'pointer',
                            display: 'inline-flex',
                            alignItems: 'center',
                          }}
                        >
                          <ExclamationTriangleIcon className="pf-v6-u-warning-color-100" />
                        </button>
                      </Tooltip>
                    )}
                  </Td>
                  <Td dataLabel="Discovery Date">
                    {repo.discovery_date
                      ? formatDate(repo.discovery_date)
                      : 'N/A'}
                  </Td>
                  <Td dataLabel="Last Sync">
                    {repo.last_sync_date
                      ? formatDate(repo.last_sync_date)
                      : 'Never'}
                  </Td>
                  <Td dataLabel="Quay Repository">
                    {repo.quay_repository ? (
                      <Link
                        to={`/repository/${repo.quay_repository}`}
                        data-testid={`repo-link-${repo.name}`}
                      >
                        {repo.quay_repository}
                      </Link>
                    ) : (
                      'Not created'
                    )}
                  </Td>
                </Tr>
              ))}
            </Tbody>
          </Table>
          <Pagination
            itemCount={total}
            perPage={perPage}
            page={page}
            onSetPage={(_event, newPage) => setPage(newPage)}
            onPerPageSelect={(_event, newPerPage) => {
              setPerPage(newPerPage);
              setPage(1);
            }}
            variant="bottom"
            data-testid="org-mirror-repos-pagination"
          />
        </>
      )}
    </>
  );
};
