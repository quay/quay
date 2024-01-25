import {
  Alert,
  Button,
  Radio,
  Spinner,
  Title,
  Toolbar,
  ToolbarContent,
  ToolbarItem,
} from '@patternfly/react-core';
import Conditional from 'src/components/empty/Conditional';
import {useAnalyzeBuildTrigger} from 'src/hooks/UseBuildTriggers';
import {useFetchRobotAccounts} from 'src/hooks/useRobotAccounts';
import {isNullOrUndefined} from 'src/libs/utils';
import {Table, Tbody, Td, Th, Thead, Tr} from '@patternfly/react-table';
import {SearchInput} from 'src/components/toolbar/SearchInput';
import {ToolbarPagination} from 'src/components/toolbar/ToolbarPagination';
import {SearchState} from 'src/components/toolbar/SearchTypes';
import {useEffect, useState} from 'react';
import EntityComponent from 'src/components/Entity';
import {Entity, EntityKind} from 'src/resources/UserResource';
import {RepositoryBuildTriggerAnalysis} from 'src/resources/BuildResource';

export default function RobotAccounts(props: RobotAccountsProps) {
  const {
    namespace,
    repo,
    triggerUuid,
    buildSource,
    contextPath,
    dockerfilePath,
    isOrganization,
    robotAccount,
    setRobotAccount,
  } = props;
  const [search, setSearch] = useState<SearchState>({
    field: 'Robot Name',
    query: '',
  });
  const [perPage, setPerPage] = useState<number>(20);
  const [page, setPage] = useState<number>(1);
  const {analysis, isError, error, isLoading, isSuccess} =
    useAnalyzeBuildTrigger(
      namespace,
      repo,
      triggerUuid,
      buildSource,
      contextPath,
      dockerfilePath,
    );
  const {
    robots,
    isLoadingRobots,
    error: fetchingRobotsError,
    isError: isFetchingRobotsError,
  } = useFetchRobotAccounts(
    namespace,
    !isOrganization,
    !isLoading && analysis?.status === 'notimplemented',
  );

  const triggerAnalysis: RepositoryBuildTriggerAnalysis =
    !isLoading &&
    !isLoadingRobots &&
    !isError &&
    !isFetchingRobotsError &&
    analysis?.status === 'notimplemented'
      ? {
          status: 'publicbase',
          is_admin: true,
          message: '',
          robots: robots.map(
            (robot) =>
              ({name: robot.name, kind: 'user', can_read: false}) as Entity,
          ),
          namespace: namespace,
          name: repo,
        }
      : analysis;

  useEffect(() => {
    if (isSuccess) {
      props.setRobotAccountValid(
        triggerAnalysis?.status !== 'requiresrobot' ||
          !isNullOrUndefined(robotAccount),
      );
    }
  }, [triggerAnalysis?.status, robotAccount]);

  if (isLoading || isLoadingRobots) {
    return <Spinner />;
  }

  if (isError) {
    return <Alert variant="danger" title={error.toString()} />;
  }

  if (isFetchingRobotsError) {
    return <Alert variant="danger" title={fetchingRobotsError.toString()} />;
  }

  const filteredRobots = triggerAnalysis.robots.filter((robot) =>
    robot.name.includes(search.query),
  );
  const paginatedRobots = filteredRobots.slice(
    (page - 1) * perPage,
    page * perPage,
  );

  return (
    <>
      <Conditional if={triggerAnalysis?.status === 'warning'}>
        <Alert variant="warning" title={triggerAnalysis?.message} />
      </Conditional>
      <Conditional if={triggerAnalysis.status == 'publicbase'}>
        <Title headingLevel="h3">Optional Robot Account</Title>
        <strong>
          <Conditional if={triggerAnalysis.is_admin}>
            <span>
              Choose an optional robot account below or click &#34;Continue&#34;
              to complete setup of this build trigger.
            </span>
          </Conditional>
        </strong>
      </Conditional>
      <Conditional
        if={
          triggerAnalysis.status == 'requiresrobot' && !triggerAnalysis.is_admin
        }
      >
        <Title headingLevel="h3">Robot Account Required</Title>
        <p>
          The selected Dockerfile in the selected repository depends upon a
          private base image.
        </p>
        <p>
          A robot account with access to the base image is required to setup
          this trigger, but you are not the administrator of this namespace.
        </p>
        <p>
          Administrative access is required to continue to ensure security of
          the robot credentials.
        </p>
      </Conditional>
      <Conditional
        if={
          triggerAnalysis.status == 'requiresrobot' && triggerAnalysis.is_admin
        }
      >
        <Title headingLevel="h3">Robot Account Required</Title>
        <p>
          The selected Dockerfile in the selected repository depends upon a
          private base image.
        </p>
        <p>
          A robot account with access to the base image is required to setup
          this trigger.
        </p>
      </Conditional>

      <Conditional if={triggerAnalysis.is_admin}>
        <Toolbar>
          <ToolbarContent>
            <ToolbarItem>
              <SearchInput
                id="robotaccounts-search-input"
                searchState={search}
                onChange={setSearch}
              />
            </ToolbarItem>
            <ToolbarItem>
              <ToolbarPagination
                total={filteredRobots.length}
                perPage={perPage}
                page={page}
                setPage={setPage}
                setPerPage={setPerPage}
              />
            </ToolbarItem>
            <ToolbarItem align={{default: 'alignRight'}}>
              <Button onClick={() => setRobotAccount(null)}>Clear</Button>
            </ToolbarItem>
          </ToolbarContent>
        </Toolbar>
        <Table
          id="robot-accounts-table"
          aria-label="Build Trigger Robot Accounts"
          variant="compact"
        >
          <Thead>
            <Tr>
              <Th></Th>
              <Th>Robot Account</Th>
              <Th></Th>
            </Tr>
          </Thead>
          <Tbody>
            {paginatedRobots.map((robot) => (
              <Tr key={robot.name}>
                <Td>
                  <Radio
                    aria-label={`${robot.name} Checkbox`}
                    id={`${robot.name}-checkbox`}
                    name={`${robot.name}-checkbox`}
                    isChecked={robot.name === robotAccount}
                    onChange={(_, checked) => setRobotAccount(robot.name)}
                  />
                </Td>
                <Td>
                  <EntityComponent
                    type={EntityKind.robot}
                    name={robot.name}
                    includeIcon
                  />
                </Td>
                <Td>
                  <Conditional if={robot.can_read}>Can Read</Conditional>
                  <Conditional if={!robot.can_read}>
                    Read access will be added if selected
                  </Conditional>
                </Td>
              </Tr>
            ))}
            <Conditional if={paginatedRobots.length === 0}>
              <Tr>
                <Td colSpan={3}>
                  <p>No robots found.</p>
                </Td>
              </Tr>
            </Conditional>
          </Tbody>
        </Table>
      </Conditional>
      <br />
      <Conditional if={triggerAnalysis.is_admin}>
        <p>
          In order to pull a <b>private base image</b> during the build process,
          a robot account with access must be selected.
        </p>
        <Conditional if={triggerAnalysis.status !== 'requiresrobot'}>
          <p>
            If you know that a private base image is not used, you can skip this
            step.
          </p>
        </Conditional>
        <Conditional if={triggerAnalysis.status == 'requiresrobot'}>
          <p>
            Robot accounts that already have access to this base image are
            listed first. If you select a robot account that does not currently
            have access, read permission will be granted to that robot account
            on trigger creation.
          </p>
        </Conditional>
      </Conditional>
    </>
  );
}

interface RobotAccountsProps {
  namespace: string;
  repo: string;
  triggerUuid: string;
  buildSource: string;
  contextPath: string;
  dockerfilePath: string;
  isOrganization: boolean;
  robotAccount: string;
  setRobotAccount: (robotAccount: string) => void;
  setRobotAccountValid: (valid: boolean) => void;
}
