import {
  Alert,
  Button,
  Radio,
  Spinner,
  Toolbar,
  ToolbarContent,
  ToolbarItem,
} from '@patternfly/react-core';
import {Table, Tbody, Td, Th, Thead, Tr} from '@patternfly/react-table';
import {useState} from 'react';
import LinkOrPlainText from 'src/components/LinkOrPlainText';
import RegistryName from 'src/components/RegistryName';
import UsageIndicator from 'src/components/UsageIndicator';
import Conditional from 'src/components/empty/Conditional';
import {SearchInput} from 'src/components/toolbar/SearchInput';
import {SearchState} from 'src/components/toolbar/SearchTypes';
import {ToolbarPagination} from 'src/components/toolbar/ToolbarPagination';
import {useGitNamespaces} from 'src/hooks/UseBuildTriggers';
import {useQuayConfig} from 'src/hooks/UseQuayConfig';
import {isNullOrUndefined} from 'src/libs/utils';
import {GitNamespace} from 'src/resources/BuildResource';

export default function SelectOrganization(props: SelectOrganizationProps) {
  const {org, repo, triggerUuid, gitNamespace, setGitNamespace, service} =
    props;
  const quayConfig = useQuayConfig();
  const [search, setSearch] = useState<SearchState>({
    field: 'Namespace Name',
    query: '',
  });
  const [perPage, setPerPage] = useState<number>(20);
  const [page, setPage] = useState<number>(1);
  const {gitNamespaces, isLoading, isError, error} = useGitNamespaces(
    org,
    repo,
    triggerUuid,
  );

  if (isLoading) {
    return <Spinner />;
  }

  if (isError) {
    return <Alert variant="danger" title={error.toString()} />;
  }

  const maxScore = gitNamespaces.reduce(
    (acc, namespace) => namespace.score > acc && namespace.score,
    0,
  );

  const filteredNamespaces = gitNamespaces.filter((namespace) =>
    namespace.title.includes(search.query),
  );
  const paginatedNamespaces = filteredNamespaces.slice(
    (page - 1) * perPage,
    page * perPage,
  );

  return (
    <>
      <p>
        <b>Please select the organization under which the repository lives.</b>
      </p>
      <Toolbar>
        <ToolbarContent>
          <ToolbarItem>
            <SearchInput
              id="gitnamespaces-search-input"
              searchState={search}
              onChange={setSearch}
            />
          </ToolbarItem>
          <ToolbarItem>
            <ToolbarPagination
              total={filteredNamespaces.length}
              perPage={perPage}
              page={page}
              setPage={setPage}
              setPerPage={setPerPage}
            />
          </ToolbarItem>
          <ToolbarItem align={{default: 'alignRight'}}>
            <Button onClick={() => setGitNamespace(null)}>Clear</Button>
          </ToolbarItem>
        </ToolbarContent>
      </Toolbar>
      <Table
        id="organizations-table"
        aria-label="Organizations"
        variant="compact"
      >
        <Thead>
          <Tr>
            <Th></Th>
            <Th>Organization</Th>
            <Th></Th>
          </Tr>
        </Thead>
        <Tbody id="organizations-table-body">
          {paginatedNamespaces.map((namespace) => (
            <Tr key={namespace.id}>
              <Td>
                <Radio
                  aria-label={`${namespace.title} Checkbox`}
                  id={`${namespace.id}-checkbox`}
                  name={`${namespace.title}-checkbox`}
                  isChecked={namespace.title === gitNamespace?.title}
                  onChange={(_, checked) => setGitNamespace(namespace)}
                />
              </Td>
              <Td>
                <Conditional if={!isNullOrUndefined(namespace.avatar_url)}>
                  <img
                    src={namespace.avatar_url}
                    alt={namespace.title}
                    style={{width: '1em', height: '1em', marginRight: '1em'}}
                  />
                </Conditional>
                <LinkOrPlainText href={namespace.url}>
                  {namespace.title}
                </LinkOrPlainText>
              </Td>
              <Td>
                <UsageIndicator value={namespace.score} max={maxScore} />
              </Td>
            </Tr>
          ))}
          <Conditional if={paginatedNamespaces.length === 0}>
            <Tr>
              <Td colSpan={3}>
                <p>No organizations found.</p>
              </Td>
            </Tr>
          </Conditional>
        </Tbody>
      </Table>
      <br />
      <p>
        <RegistryName /> has been granted access to read and view these
        organizations
      </p>
      <br />
      <Conditional if={service === 'github'}>
        <Alert
          id="select-organization-informational-alert"
          title={
            <>
              <b>Don&#39;t see an expected organization here? </b>Please visit{' '}
              <a
                href={`${quayConfig.oauth['GITHUB_TRIGGER_CONFIG']['GITHUB_ENDPOINT']}settings/connections/applications/${quayConfig.oauth['GITHUB_TRIGGER_CONFIG']['CLIENT_ID']}`}
                target="_blank"
                rel="nofollow noopener noreferrer"
              >
                Connections with <RegistryName />
              </a>{' '}
              and choose <code>Grant</code> or <code>Request</code> before
              reloading this page.
            </>
          }
        />
      </Conditional>
    </>
  );
}

interface SelectOrganizationProps {
  org: string;
  repo: string;
  triggerUuid: string;
  gitNamespace: GitNamespace;
  setGitNamespace: (gitNamespace: GitNamespace) => void;
  service: string;
}
