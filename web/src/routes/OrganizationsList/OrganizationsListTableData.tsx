import {Td} from '@patternfly/react-table';
import {Skeleton, Flex, FlexItem} from '@patternfly/react-core';
import './css/Organizations.scss';
import {Link} from 'react-router-dom';
import {fetchOrg} from 'src/resources/OrganizationResource';
import Avatar from 'src/components/Avatar';
import {IRepository} from 'src/resources/RepositoryResource';
import {useCurrentUser} from 'src/hooks/UseCurrentUser';
import {fetchMembersForOrg} from 'src/resources/MembersResource';
import {fetchRobotsForNamespace} from 'src/resources/RobotsResource';
import {formatDate} from 'src/libs/utils';
import ColumnNames from './ColumnNames';
import {OrganizationsTableItem} from './OrganizationsList';
import {useQuery} from '@tanstack/react-query';
import OrganizationOptionsKebab from './OrganizationOptionsKebab';
import {useRepositories} from 'src/hooks/UseRepositories';
import {renderQuotaConsumed} from 'src/libs/quotaUtils';
import {useQuayConfig} from 'src/hooks/UseQuayConfig';

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

interface OrgTableDataProps extends OrganizationsTableItem {
  userEmail?: string;
  quota_report?: import('src/libs/quotaUtils').IQuotaReport;
}

// Get and assemble data from multiple endpoints to show in Org table
// Only necessary because current API structure does not return all required data
export default function OrgTableData(props: OrgTableDataProps) {
  const config = useQuayConfig();
  // Get current user data for user avatars
  const {user: currentUser} = useCurrentUser();
  // const queryClient = useQueryClient();
  // useEffect(() => {
  //   return () => {
  //     queryClient.cancelQueries(['organization', props.name]);
  //     queryClient.cancelQueries(['organization', props.name, 'members']);
  //     queryClient.cancelQueries(['organization', props.name, 'robots']);
  //     queryClient.cancelQueries(['organization', props.name, 'repositories']);
  //   };
  // }, [props.name]);

  const {isSuperUser} = useCurrentUser();

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
  const lastModifiedDate = getLastModifiedRepoTime(
    Array.isArray(repositories) &&
      repositories.length > 0 &&
      !Array.isArray(repositories[0])
      ? (repositories as IRepository[])
      : [],
  );

  let teamCountVal: string;
  if (!props.isUser) {
    useQuery(
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
        <Flex alignItems={{default: 'alignItemsCenter'}}>
          {/* Show avatar for organizations OR current user */}
          {((props.isUser &&
            currentUser?.username === props.name &&
            currentUser?.avatar) ||
            (!props.isUser && organization?.avatar)) && (
            <FlexItem spacer={{default: 'spacerSm'}}>
              <Avatar
                avatar={
                  props.isUser ? currentUser?.avatar : organization?.avatar
                }
                size="sm"
              />
            </FlexItem>
          )}
          <FlexItem>
            <Link to={props.name}>{props.name}</Link>
          </FlexItem>
        </Flex>
      </Td>
      {isSuperUser && config?.features?.MAILING && (
        <Td dataLabel={ColumnNames.adminEmail}>
          {props.isUser ? (
            props.userEmail ? (
              <a href={`mailto:${props.userEmail}`}>{props.userEmail}</a>
            ) : (
              <span style={{color: '#888'}}>—</span>
            )
          ) : organization?.email ? (
            <a href={`mailto:${organization.email}`}>{organization.email}</a>
          ) : (
            <span style={{color: '#888'}}>—</span>
          )}
        </Td>
      )}
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
      {isSuperUser &&
        config?.features?.QUOTA_MANAGEMENT &&
        config?.features?.EDIT_QUOTA && (
          <Td dataLabel={ColumnNames.size}>
            {props.isUser ? (
              props.quota_report ? (
                renderQuotaConsumed(props.quota_report, {
                  showPercentage: true,
                  showTotal: true,
                  showBackfill: true,
                })
              ) : (
                <span style={{color: '#888'}}>—</span>
              )
            ) : (
              renderQuotaConsumed(
                props.quota_report || organization?.quota_report,
                {
                  showPercentage: true,
                  showTotal: true,
                  showBackfill: true,
                },
              )
            )}
          </Td>
        )}
      {isSuperUser && (
        <Td dataLabel={ColumnNames.options}>
          <OrganizationOptionsKebab
            name={props.name}
            isUser={props.isUser}
            userEnabled={props.userEnabled}
            userSuperuser={props.userSuperuser}
          />
        </Td>
      )}
    </>
  );
}
