import {
  Alert,
  Button,
  Checkbox,
  Radio,
  Spinner,
  Toolbar,
  ToolbarContent,
  ToolbarItem,
  Tooltip,
} from '@patternfly/react-core';
import {ExclamationTriangleIcon} from '@patternfly/react-icons';
import {Table, Tbody, Td, Th, Thead, Tr} from '@patternfly/react-table';
import {useState} from 'react';
import Conditional from 'src/components/empty/Conditional';
import {SearchInput} from 'src/components/toolbar/SearchInput';
import {SearchState} from 'src/components/toolbar/SearchTypes';
import {ToolbarPagination} from 'src/components/toolbar/ToolbarPagination';
import {useGitSources} from 'src/hooks/UseBuildTriggers';
import {humanizeTimeForExpiry, isNullOrUndefined} from 'src/libs/utils';
import {GitNamespace} from 'src/resources/BuildResource';
import ServiceIcon from './BuildsServiceIcon';

export default function HostedRepository(props: HostedRepositoryProps) {
  const {org, repo, triggerUuid, repoUrl, setRepoUrl, gitNamespace, service} =
    props;
  const {sources, isLoading, error, isError} = useGitSources(
    org,
    repo,
    triggerUuid,
    gitNamespace.id,
  );
  const [search, setSearch] = useState<SearchState>({
    field: 'Filter repositories...',
    query: '',
  });
  const [hideStale, setHideStale] = useState<boolean>(true);
  const [perPage, setPerPage] = useState<number>(20);
  const [page, setPage] = useState<number>(1);

  if (isLoading) {
    return <Spinner />;
  }

  if (isError) {
    return <Alert variant="danger" title={error.toString()} />;
  }

  const filteredSources = sources.filter((source) => {
    const filterByName =
      search.query !== ''
        ? source.name.includes(search.query) ||
          source.description.includes(search.query)
        : true;
    let filterByDate = true;
    if (hideStale) {
      filterByDate =
        new Date(source.last_updated * 1000) >
        new Date(Date.now() - 1000 * 60 * 60 * 24 * 30);
    }
    return filterByName && filterByDate;
  });
  const paginatedSources = filteredSources.slice(
    (page - 1) * perPage,
    page * perPage,
  );

  return (
    <>
      <p>
        <b id="hosted-repository-header-description">
          Select a repository in{' '}
          <Conditional if={!isNullOrUndefined(gitNamespace.avatar_url)}>
            <img
              style={{height: '1em', width: '1em', marginRight: '1em'}}
              src={gitNamespace.avatar_url}
            />
          </Conditional>
          {gitNamespace.title}
        </b>
      </p>
      <Toolbar>
        <ToolbarContent>
          <ToolbarItem>
            <SearchInput
              id="hostedrepositories-search-input"
              searchState={search}
              onChange={setSearch}
            />
          </ToolbarItem>
          <ToolbarItem>
            <ToolbarPagination
              total={filteredSources.length}
              perPage={perPage}
              page={page}
              setPage={setPage}
              setPerPage={setPerPage}
            />
          </ToolbarItem>
          <ToolbarItem align={{default: 'alignRight'}}>
            <Checkbox
              id="hide-stale-checkbox"
              label="Hide stale repositories"
              isChecked={hideStale}
              onChange={(_, checked) => setHideStale(checked)}
            />
          </ToolbarItem>
          <ToolbarItem align={{default: 'alignRight'}}>
            <Button onClick={() => setRepoUrl(null)}>Clear</Button>
          </ToolbarItem>
        </ToolbarContent>
      </Toolbar>
      <Table
        id="hosted-repositories-table"
        aria-label="Hosted Repositories Table"
        variant="compact"
      >
        <Thead>
          <Tr>
            <Th></Th>
            <Th>Repository Name</Th>
            <Th>Last Updated</Th>
            <Th>Description</Th>
          </Tr>
        </Thead>
        <Tbody>
          {paginatedSources.map((source) => (
            <Tr key={source.name}>
              <Td>
                <Conditional if={!source.has_admin_permissions}>
                  <Tooltip content="Admin access is required to add the webhook trigger to this repository">
                    <ExclamationTriangleIcon
                      id={`${source.name}-admin-access-required-tooltip`}
                    />
                  </Tooltip>
                </Conditional>
                <Conditional if={source.has_admin_permissions}>
                  <Radio
                    aria-label={`${source.name} Checkbox`}
                    id={`${source.name}-checkbox`}
                    name={`${source.name}-checkbox`}
                    isChecked={source.full_name === repoUrl}
                    onChange={(_, checked) => setRepoUrl(source.full_name)}
                  />
                </Conditional>
              </Td>
              <Td>
                <ServiceIcon service={service} />
                <a href={source.url}> {source.name}</a>
              </Td>
              <Td>
                {humanizeTimeForExpiry(
                  (new Date().getTime() -
                    new Date(source.last_updated * 1000).getTime()) /
                    1000,
                )}
              </Td>
              <Td>
                <Conditional if={!isNullOrUndefined(source.description)}>
                  {source.description}
                </Conditional>
                <Conditional
                  if={
                    isNullOrUndefined(source.description) ||
                    source.description === ''
                  }
                >
                  <span style={{color: 'lightgrey'}}>None</span>
                </Conditional>
              </Td>
            </Tr>
          ))}
        </Tbody>
      </Table>
      <br />
      <p>
        A webhook will be added to the selected repository in order to detect
        when new commits are made.
      </p>
      <p>
        Don&#39;t see an expected repository here? Please make sure you have
        admin access on that repository.
      </p>
    </>
  );
}

interface HostedRepositoryProps {
  org: string;
  repo: string;
  triggerUuid: string;
  repoUrl: string;
  setRepoUrl: (repoUrl: string) => void;
  gitNamespace: GitNamespace;
  service: string;
}
