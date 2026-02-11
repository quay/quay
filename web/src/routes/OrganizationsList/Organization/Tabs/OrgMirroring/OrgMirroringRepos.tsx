import React, {useState} from 'react';
import {
  Divider,
  Title,
  Label,
  Pagination,
  Spinner,
  Text,
} from '@patternfly/react-core';
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
}

// Repo-level statuses reuse the org-level maps, with one extra status
const repoStatusColors: Record<
  string,
  'blue' | 'green' | 'red' | 'cyan' | 'orange' | 'grey'
> = {
  ...orgMirrorStatusColors,
  DISCOVERED: 'grey',
};

const repoStatusLabels: Record<string, string> = {
  ...orgMirrorStatusLabels,
  NEVER_RUN: 'Pending',
  SYNC_NOW: 'Scheduled',
  DISCOVERED: 'Discovered',
};

export const OrgMirroringRepos: React.FC<OrgMirroringReposProps> = ({
  config,
  orgName,
}) => {
  const [page, setPage] = useState(1);
  const [perPage, setPerPage] = useState(20);

  const {
    data,
    isLoading,
    error: queryError,
  } = useQuery<OrgMirrorReposResponse>({
    queryKey: ['org-mirror-repos', orgName, page, perPage],
    queryFn: () => getOrgMirrorRepos(orgName, page, perPage),
    enabled: !!config,
    refetchInterval: config?.sync_status === 'SYNCING' ? 5000 : false,
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
        <Text component="p" className="pf-v5-u-danger-color-100">
          {error}
        </Text>
      )}

      {!isLoading && !error && repos.length === 0 && (
        <Text component="p">
          No repositories discovered yet. Repositories will appear here after
          the first sync.
        </Text>
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
