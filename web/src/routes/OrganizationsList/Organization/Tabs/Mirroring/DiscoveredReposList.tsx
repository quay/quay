import {
  Button,
  EmptyState,
  EmptyStateBody,
  EmptyStateIcon,
  Pagination,
  Popover,
  Title,
} from '@patternfly/react-core';
import {ExclamationCircleIcon, SearchIcon} from '@patternfly/react-icons';
import {Table, Tbody, Td, Th, Thead, Tr} from '@patternfly/react-table';
import {useState} from 'react';
import {Link} from 'react-router-dom';
import {DiscoveredRepository} from 'src/resources/OrgMirrorResource';
import RepoStatusBadge from './RepoStatusBadge';

interface DiscoveredReposListProps {
  repos: DiscoveredRepository[];
  organizationName: string;
  isLoading?: boolean;
}

export default function DiscoveredReposList({
  repos,
  organizationName,
  isLoading = false,
}: DiscoveredReposListProps) {
  const [page, setPage] = useState(1);
  const [perPage, setPerPage] = useState(10);

  if (!repos || repos.length === 0) {
    return (
      <EmptyState>
        <EmptyStateIcon icon={SearchIcon} />
        <Title headingLevel="h4" size="lg">
          No repositories discovered yet
        </Title>
        <EmptyStateBody>
          Repositories will appear here after the first sync completes.
        </EmptyStateBody>
      </EmptyState>
    );
  }

  // Paginate repos
  const startIndex = (page - 1) * perPage;
  const endIndex = startIndex + perPage;
  const paginatedRepos = repos.slice(startIndex, endIndex);

  const handleSetPage = (
    _event: React.MouseEvent | React.KeyboardEvent | MouseEvent,
    newPage: number,
  ) => {
    setPage(newPage);
  };

  const handlePerPageSelect = (
    _event: React.MouseEvent | React.KeyboardEvent | MouseEvent,
    newPerPage: number,
    newPage: number,
  ) => {
    setPerPage(newPerPage);
    setPage(newPage);
  };

  return (
    <>
      <Table
        aria-label="Discovered repositories"
        data-testid="discovered-repos-table"
      >
        <Thead>
          <Tr>
            <Th>Repository Name</Th>
            <Th>External Repository</Th>
            <Th>Status</Th>
            <Th>Actions</Th>
          </Tr>
        </Thead>
        <Tbody>
          {paginatedRepos.map((repo) => (
            <Tr
              key={repo.repository_name}
              data-testid={`repo-row-${repo.repository_name}`}
            >
              <Td dataLabel="Repository Name">
                {repo.created_repository ? (
                  <Link to={`/repository/${repo.created_repository}`}>
                    {repo.repository_name}
                  </Link>
                ) : (
                  repo.repository_name
                )}
              </Td>
              <Td dataLabel="External Repository">{repo.external_repo_name}</Td>
              <Td dataLabel="Status">
                <RepoStatusBadge status={repo.status} />
                {repo.message && repo.status === 'FAILED' && (
                  <Popover
                    headerContent="Error Details"
                    bodyContent={repo.message}
                    data-testid={`error-popover-${repo.repository_name}`}
                  >
                    <Button
                      variant="link"
                      icon={<ExclamationCircleIcon />}
                      style={{marginLeft: '0.5rem'}}
                      data-testid={`view-error-btn-${repo.repository_name}`}
                    >
                      View Error
                    </Button>
                  </Popover>
                )}
              </Td>
              <Td dataLabel="Actions">
                {repo.created_repository && (
                  <Button
                    variant="link"
                    component={(props) => (
                      <Link
                        {...props}
                        to={`/repository/${repo.created_repository}`}
                      />
                    )}
                    data-testid={`view-repo-btn-${repo.repository_name}`}
                  >
                    View Repository
                  </Button>
                )}
              </Td>
            </Tr>
          ))}
        </Tbody>
      </Table>
      <Pagination
        itemCount={repos.length}
        perPage={perPage}
        page={page}
        onSetPage={handleSetPage}
        onPerPageSelect={handlePerPageSelect}
        perPageOptions={[
          {title: '10', value: 10},
          {title: '20', value: 20},
          {title: '50', value: 50},
        ]}
        data-testid="discovered-repos-pagination"
      />
    </>
  );
}
