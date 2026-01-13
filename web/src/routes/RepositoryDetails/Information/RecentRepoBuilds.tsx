import {
  Card,
  CardBody,
  CardTitle,
  Flex,
  Spinner,
  Text,
  TextContent,
  TextVariants,
  Tooltip,
} from '@patternfly/react-core';
import {OutlinedClockIcon} from '@patternfly/react-icons';
import {Link, useLocation} from 'react-router-dom';
import moment from 'moment';
import {useRecentBuilds} from 'src/hooks/UseBuilds';
import {
  BuildPhase,
  TriggeredBuildDescription,
} from 'src/routes/RepositoryDetails/Builds/BuildHistory';
import {RepositoryBuild} from 'src/resources/BuildResource';
import {getBuildInfoPath} from 'src/routes/NavigationPath';
import {formatDate} from 'src/libs/utils';
import './Information.css';

interface RecentRepoBuildsProps {
  organization: string;
  repository: string;
  canWrite: boolean;
  canAdmin: boolean;
}

export default function RecentRepoBuilds({
  organization,
  repository,
  canWrite,
  canAdmin,
}: RecentRepoBuildsProps) {
  const location = useLocation();
  const {builds, isLoading, isError} = useRecentBuilds(
    organization,
    repository,
    3,
  );

  // Format relative time like "6 hours ago"
  const formatRelativeTime = (dateString: string): string => {
    return moment(dateString).fromNow();
  };

  return (
    <Card>
      <CardTitle>Recent Repo Builds</CardTitle>
      <CardBody>
        {/* Loading State */}
        {isLoading && (
          <Flex justifyContent={{default: 'justifyContentCenter'}}>
            <Spinner size="md" />
          </Flex>
        )}

        {/* Error State */}
        {isError && (
          <TextContent>
            <Text component={TextVariants.small}>
              Unable to load recent builds.
            </Text>
          </TextContent>
        )}

        {/* Empty State */}
        {!isLoading && !isError && (!builds || builds.length === 0) && (
          <div className="recent-builds-empty">
            <TextContent>
              <Text component={TextVariants.p}>
                No builds have been run for this repository.
              </Text>
              {canWrite && (
                <Text component={TextVariants.small}>
                  Click on the Builds tab to start a new build.
                </Text>
              )}
            </TextContent>
          </div>
        )}

        {/* Builds List */}
        {!isLoading && !isError && builds && builds.length > 0 && (
          <>
            <div className="recent-builds-list">
              {builds.map((build: RepositoryBuild) => (
                <Link
                  key={build.id}
                  to={getBuildInfoPath(
                    location.pathname,
                    organization,
                    repository,
                    build.id,
                  )}
                  className="recent-build-item-link"
                >
                  <div className="recent-build-item">
                    <BuildPhase phase={build.phase} hideText={true} />
                    <Tooltip content={formatDate(build.started)}>
                      <span className="recent-build-timing">
                        <OutlinedClockIcon />
                        <span>{formatRelativeTime(build.started)}</span>
                      </span>
                    </Tooltip>
                    <span className="recent-build-description">
                      <TriggeredBuildDescription build={build} />
                    </span>
                  </div>
                </Link>
              ))}
            </div>

            {/* View Build History Link */}
            {canWrite && (
              <div className="view-build-history-link">
                <Link to={`${location.pathname}?tab=builds`}>
                  View Build History
                </Link>
              </div>
            )}
          </>
        )}
      </CardBody>
    </Card>
  );
}
