import {Td} from '@patternfly/react-table';
import {Skeleton} from '@patternfly/react-core';
import './css/Organizations.scss';
import {Link} from 'react-router-dom';
import {fetchOrg} from 'src/resources/OrganizationResource';
import {
  fetchRepositoriesForNamespace,
  IRepository,
} from 'src/resources/RepositoryResource';
import {fetchMembersForOrg} from 'src/resources/MembersResource';
import {fetchRobotsForNamespace} from 'src/resources/RobotsResource';
import {formatDate} from 'src/libs/utils';
import ColumnNames from './ColumnNames';
import {OrganizationsTableItem} from './OrganizationsList';
import {useQuery, useQueryClient} from '@tanstack/react-query';
import {useRepositories} from 'src/hooks/UseRepositories';

interface CountProps {
  count: string | number;
}

interface RepoLastModifiedDateProps {
  lastModifiedDate: number;
}

function Count(props: CountProps) {
  return <>{props.count !== null ? props.count : <Skeleton width="100%" />}</>;
}

function RepoLastModifiedDate(props: RepoLastModifiedDateProps) {
  return (
    <>
      {props.lastModifiedDate !== 0 ? (
        formatDate(props.lastModifiedDate)
      ) : (
        <Skeleton width="100%" />
      )}
    </>
  );
}

// Get and assemble data from multiple endpoints to show in Org table
// Only necessary because current API structure does not return all required data
export default function OrgTableData(props: OrganizationsTableItem) {
  // const queryClient = useQueryClient();
  // useEffect(() => {
  //   return () => {
  //     queryClient.cancelQueries(['organization', props.name]);
  //     queryClient.cancelQueries(['organization', props.name, 'members']);
  //     queryClient.cancelQueries(['organization', props.name, 'robots']);
  //     queryClient.cancelQueries(['organization', props.name, 'repositories']);
  //   };
  // }, [props.name]);
  // Get organization
  const {data: organization} = useQuery(
    ['organization', props.name],
    ({signal}) => fetchOrg(props.name, signal),
    {enabled: !props.isUser},
  );

  // Get members
  const {data: members} = useQuery(
    ['organization', props.name, 'members'],
    ({signal}) => fetchMembersForOrg(props.name, signal),
    {placeholderData: props.isUser ? [] : undefined},
  );
  const memberCount = props.isUser ? 0 : members ? members.length : null;

  // Get robots
  const {data: robots} = useQuery(
    ['organization', props.name, 'robots'],
    ({signal}) => fetchRobotsForNamespace(props.name, false, signal),
  );
  const robotCount = robots ? robots.length : null;

  // Get repositories
  const {repos: repositories, totalResults: repoCount} = useRepositories(
    props.name,
  );

  const getLastModifiedRepoTime = (repos: IRepository[]) => {
    // get the repo with the most recent last modified
    if (!repos || !repos.length) {
      return -1;
    }

    const recentRepo = repos.reduce((prev, curr) =>
      prev.last_modified < curr.last_modified ? curr : prev,
    );
    return recentRepo.last_modified || -1;
  };
  const lastModifiedDate = getLastModifiedRepoTime(repositories);

  let teamCountVal: string;
  if (!props.isUser) {
    const {data: teams} = useQuery(
      ['organization', props.name, 'teams'],
      () => organization?.teams || [],
    );
    teamCountVal = organization?.teams
      ? Object.keys(organization?.teams)?.length.toString()
      : '0';
  } else {
    teamCountVal = 'N/A';
  }

  return (
    <>
      <Td dataLabel={ColumnNames.name}>
        <Link to={props.name}>{props.name}</Link>
      </Td>
      <Td dataLabel={ColumnNames.repoCount}>
        <Count count={repoCount}></Count>
      </Td>
      <Td dataLabel={ColumnNames.teamsCount}>
        <Count count={teamCountVal}></Count>
      </Td>
      <Td dataLabel={ColumnNames.membersCount}>
        <Count count={memberCount}></Count>
      </Td>
      <Td dataLabel={ColumnNames.robotsCount}>
        <Count count={robotCount}></Count>
      </Td>
      <Td dataLabel={ColumnNames.lastModified}>
        <RepoLastModifiedDate
          lastModifiedDate={lastModifiedDate}
        ></RepoLastModifiedDate>
      </Td>
    </>
  );
}
