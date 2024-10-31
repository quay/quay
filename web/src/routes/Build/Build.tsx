import {
  Alert,
  Button,
  Card,
  CardBody,
  CardTitle,
  CodeBlock,
  CodeBlockAction,
  CodeBlockCode,
  DescriptionList,
  DescriptionListDescription,
  DescriptionListGroup,
  DescriptionListTerm,
  Flex,
  FlexItem,
  Modal,
  ModalVariant,
  Spinner,
} from '@patternfly/react-core';
import {useLocation, useNavigate} from 'react-router-dom';
import {LoadingPage} from 'src/components/LoadingPage';
import RequestError from 'src/components/errors/RequestError';
import {
  BuildLogEntry,
  useBuild,
  useBuildLogs,
  useCancelBuild,
} from 'src/hooks/UseBuilds';
import {
  escapeHtmlString,
  formatDate,
  isNullOrUndefined,
  parseOrgNameFromUrl,
  parseRepoNameFromUrl,
} from 'src/libs/utils';
import {
  BuildPhase,
  TriggeredBuildDescription,
} from 'src/routes/RepositoryDetails/Builds/BuildHistory';
import Conditional from 'src/components/empty/Conditional';
import {useAlerts} from 'src/hooks/UseAlerts';
import {AlertVariant} from 'src/atoms/AlertState';
import {useEffect, useState} from 'react';
import {
  AngleDownIcon,
  AngleRightIcon,
  CopyIcon,
  DownloadIcon,
  ExclamationTriangleIcon,
} from '@patternfly/react-icons';
import './Build.css';
import {useQuayConfig} from 'src/hooks/UseQuayConfig';
import {AxiosError} from 'axios';
import {getBuildMessage, getCompletedBuildPhases} from './Utils';
import {useRepository} from 'src/hooks/UseRepository';
import {RepositoryBuildPhase} from 'src/resources/BuildResource';

export default function Build() {
  const location = useLocation();
  const navigate = useNavigate();
  const {addAlert} = useAlerts();
  const [poll, setPoll] = useState<boolean>(true);
  const [showTimestamps, setShowTimestamps] = useState<boolean>(false);
  const [modalOpen, setModalOpen] = useState<boolean>(false);
  const org = parseOrgNameFromUrl(location.pathname);
  const repo = parseRepoNameFromUrl(location.pathname);
  const splitBy = '/build/';
  const lastIndex = location.pathname.lastIndexOf(splitBy);
  if (lastIndex === -1) {
    // Never reached since the routing rule will always contain "/build/"
    return;
  }
  const buildId = location.pathname.substring(
    lastIndex + splitBy.length,
    location.pathname.length,
  );
  const {
    repoDetails,
    isLoading: isLoadingRepo,
    isError: isErrorRepo,
    errorLoadingRepoDetails: errorRepo,
  } = useRepository(org, repo);
  const {build, isLoading, isError, error} = useBuild(
    org,
    repo,
    buildId,
    poll ? 10000 : null,
  );
  const {
    logs,
    isLoading: isLoadingLogs,
    isError: isLogsError,
    error: logsError,
  } = useBuildLogs(org, repo, buildId, poll ? 10000 : null);
  const {cancelBuild} = useCancelBuild(org, repo, buildId, {
    onSuccess: () => {
      addAlert({
        title: `Build ${buildId} cancelled`,
        variant: AlertVariant.Success,
      });
      navigate(`/repository/${org}/${repo}?tab=builds`);
    },
    onError: (error) => {
      addAlert({
        title: `Failed to cancel build ${buildId}`,
        variant: AlertVariant.Failure,
        message: error.toString(),
      });
    },
  });
  useEffect(() => {
    if (
      isLogsError ||
      isError ||
      isErrorRepo ||
      getCompletedBuildPhases().includes(build?.phase)
    ) {
      setPoll(false);
    }
  }, [isError, isLogsError, isErrorRepo, build?.phase]);

  if (isLoading || isLoadingRepo) {
    return <LoadingPage />;
  }

  if (isErrorRepo) {
    return (
      <RequestError
        message={'Could not load repository;' + errorRepo.toString()}
      />
    );
  }

  if (isError) {
    return (
      <RequestError message={'Could not load build;' + error.toString()} />
    );
  }

  if (!repoDetails?.can_write && !repoDetails?.can_admin) {
    return <RequestError message="Unauthorized" />;
  }

  const onCopy = async () => {
    const logsElement = document.getElementById('build-logs');
    try {
      await navigator.clipboard.writeText(logsElement.innerText);
    } catch (error) {
      console.error(error.message);
    }
  };

  return (
    <>
      <Card ouiaId="build-info-card">
        <CardTitle>Build Information</CardTitle>
        <CardBody>
          <Flex>
            <FlexItem>
              <DescriptionList columnModifier={{default: '2Col'}}>
                <DescriptionListGroup id="build-id">
                  <DescriptionListTerm>Build ID</DescriptionListTerm>
                  <DescriptionListDescription>
                    {build.id}
                  </DescriptionListDescription>
                </DescriptionListGroup>
                <DescriptionListGroup id="triggered-by">
                  <DescriptionListTerm>Triggered by</DescriptionListTerm>
                  <DescriptionListDescription>
                    <Conditional
                      if={
                        !isNullOrUndefined(build.trigger) ||
                        !isNullOrUndefined(build.trigger_metadata)
                      }
                    >
                      <TriggeredBuildDescription build={build} />
                    </Conditional>
                    <Conditional
                      if={
                        isNullOrUndefined(build.trigger) &&
                        isNullOrUndefined(build.trigger_metadata)
                      }
                    >
                      Manually started build
                    </Conditional>
                  </DescriptionListDescription>
                </DescriptionListGroup>
                <DescriptionListGroup id="status">
                  <DescriptionListTerm>Status</DescriptionListTerm>
                  <DescriptionListDescription>
                    <BuildPhase phase={build.phase} hideText />{' '}
                    {getBuildMessage(build.phase)}
                  </DescriptionListDescription>
                </DescriptionListGroup>
                <DescriptionListGroup id="started">
                  <DescriptionListTerm>Started</DescriptionListTerm>
                  <DescriptionListDescription>
                    {formatDate(build.started)}
                  </DescriptionListDescription>
                </DescriptionListGroup>
              </DescriptionList>
            </FlexItem>
            <Conditional if={!getCompletedBuildPhases().includes(build?.phase)}>
              <FlexItem align={{default: 'alignRight'}}>
                <Button onClick={() => setModalOpen(true)}>Cancel build</Button>
              </FlexItem>
            </Conditional>
          </Flex>
        </CardBody>
      </Card>
      <Card ouiaId="build-logs-card">
        <CardTitle>Build Logs</CardTitle>
        <CardBody>
          <Conditional if={!isLogsError && !isLoadingLogs}>
            <CodeBlock
              actions={[
                <CodeBlockAction key="copy-logs" style={{margin: '.3em'}}>
                  <Button key="copy" onClick={onCopy}>
                    <CopyIcon /> Copy
                  </Button>
                </CodeBlockAction>,
                <CodeBlockAction key="download-logs" style={{margin: '.3em'}}>
                  <Conditional if={logs?.length > 0}>
                    <a
                      target="_blank"
                      href={`/buildlogs/${build.id}`}
                      rel="noreferrer"
                    >
                      <Button key="download" id="download-button">
                        <DownloadIcon /> Download
                      </Button>
                    </a>
                  </Conditional>
                </CodeBlockAction>,
                <CodeBlockAction
                  key="toggle-timestamps"
                  style={{margin: '.3em'}}
                >
                  <Button
                    id="toggle-timestamps-button"
                    onClick={() => setShowTimestamps(!showTimestamps)}
                  >
                    {showTimestamps ? 'Hide' : 'Show'} timestamps
                  </Button>
                </CodeBlockAction>,
              ]}
            >
              <CodeBlockCode id="build-logs">
                <Conditional if={build.phase == RepositoryBuildPhase.WAITING}>
                  <span style={{color: 'darkgrey'}}>
                    Waiting for build to start
                  </span>
                </Conditional>
                {logs.map((log, index) => (
                  <BuildLog
                    key={`log${index}`}
                    entry={log}
                    index={index}
                    entries={logs}
                    showTimestamps={showTimestamps}
                  />
                ))}
              </CodeBlockCode>
            </CodeBlock>
          </Conditional>
          <Conditional if={isLogsError}>
            <Alert
              variant="danger"
              title={
                (logsError as AxiosError)?.status === 403
                  ? 'You are not authorized to view builds logs. Please have the owner of the repository grant you admin access to this repository.'
                  : 'Failed to load builds logs. Please reload and try again. If this problem persists, please check for JavaScript or networking issues and contact support.'
              }
            />
          </Conditional>
          <Conditional if={isLoadingLogs}>
            <Spinner />
          </Conditional>
        </CardBody>
      </Card>
      <Modal
        variant={ModalVariant.small}
        isOpen={modalOpen}
        onClose={() => setModalOpen(false)}
        actions={[
          <Button key="confirm" variant="primary" onClick={() => cancelBuild()}>
            Cancel build
          </Button>,
          <Button
            key="cancel"
            variant="link"
            onClick={() => setModalOpen(false)}
          >
            Cancel
          </Button>,
        ]}
      >
        Are you sure you want to cancel this build?
      </Modal>
    </>
  );
}

function BuildLog({
  entry,
  index,
  entries,
  showTimestamps,
}: {
  entry: BuildLogEntry;
  index: number;
  entries: BuildLogEntry[];
  showTimestamps: boolean;
}) {
  const [isExpanded, setIsExpanded] = useState<boolean>(false);
  return (
    <>
      <div
        className="log-header"
        style={{
          paddingTop: '.5em',
          paddingBottom: '.5em',
          marginLeft: entry.type == 'command' ? '2em' : 'default',
        }}
      >
        <Flex
          alignItems={{default: 'alignItemsFlexStart'}}
          onClick={() => setIsExpanded(!isExpanded)}
        >
          <FlexItem>
            <Conditional if={entry.logs.length > 0}>
              <span>
                <Conditional if={isExpanded}>
                  <AngleDownIcon />
                </Conditional>
                <Conditional if={!isExpanded}>
                  <AngleRightIcon />
                </Conditional>
              </span>
            </Conditional>
            <Conditional
              if={isNullOrUndefined(entry) || entry.logs.length === 0}
            >
              <div style={{width: '1em'}}></div>
            </Conditional>
          </FlexItem>
          <FlexItem style={{width: '90%'}}>
            <Conditional if={entry.type == 'phase'}>
              <span className={`phase-icon ${entry.message}`}></span>
              <span className="build-message">{entry.message}</span>
            </Conditional>
            <Conditional if={entry.type == 'error'}>
              <ExclamationTriangleIcon />
              <BuildLogError entry={entry} entries={entries} />
            </Conditional>
            <Conditional if={entry.type == 'command'}>
              <BuildLogCommand entry={entry} />
            </Conditional>
          </FlexItem>
        </Flex>
        <Conditional if={isExpanded}>
          <div style={{marginLeft: '2em'}} className="container-logs">
            {entry.logs.map((log, index) => (
              <div key={index} style={{display: 'flex'}}>
                <Conditional if={showTimestamps}>
                  <div className="build-log-timestamp">
                    {log?.data?.datetime && formatDate(log?.data?.datetime)}{' '}
                  </div>
                </Conditional>
                <div>{log.message}</div>
              </div>
            ))}
          </div>
        </Conditional>
      </div>
    </>
  );
}

function BuildLogCommand({entry}: {entry: BuildLogEntry}) {
  const config = useQuayConfig();
  const domain = config?.config.SERVER_HOSTNAME;
  const getWithoutStep = function (fullTitle) {
    const colon = fullTitle.indexOf(':');
    if (colon <= 0) {
      return '';
    }

    return fullTitle.substring(colon + 1).trim();
  };

  const isSecondaryFrom = function (fullTitle) {
    if (!fullTitle) {
      return false;
    }

    const command = getWithoutStep(fullTitle);
    return command.indexOf('FROM ') == 0 && fullTitle.indexOf('Step 1 ') < 0;
  };

  const fromName = function (fullTitle) {
    const command = getWithoutStep(fullTitle);
    if (command.indexOf('FROM ') != 0) {
      return null;
    }

    const parts = command.split(' ');
    for (let i = 0; i < parts.length - 1; i++) {
      const part = parts[i];
      if (part.trim() == 'as') {
        return parts[i + 1];
      }
    }
    return null;
  };

  const registryHandlers = {
    'quay.io': function (pieces) {
      const rnamespace = pieces[pieces.length - 2];
      const rname = pieces[pieces.length - 1].split(':')[0];
      return '/repository/' + rnamespace + '/' + rname + '/';
    },

    '': function (pieces) {
      const rnamespace = pieces.length == 1 ? '_' : 'u/' + pieces[0];
      const rname = pieces[pieces.length - 1].split(':')[0];
      return (
        'https://registry.hub.docker.com/' + rnamespace + '/' + rname + '/'
      );
    },
  };
  registryHandlers[domain] = registryHandlers['quay.io'];

  const getCommandKind = (command: string): string => {
    command = command.trim();
    if (!command) {
      return '';
    }

    const space = command.indexOf(' ');
    return command.substring(0, space);
  };

  const getCommandTitleHtml = (command: string) => {
    command = command.trim();
    if (!command) {
      return '';
    }

    const kindHandlers = {
      FROM: (command) => {
        const parts = command.split(' ');
        const pieces = parts[0].split('/');
        const registry = pieces.length < 3 ? '' : pieces[0];
        if (!registryHandlers[registry]) {
          return command;
        }
        return (
          <>
            <a
              href={registryHandlers[registry](pieces)}
              target="_blank"
              rel="noreferrer"
            >
              {parts[0]}
            </a>{' '}
            {parts.splice(1).join(' ')}
          </>
        );
      },
    };

    const space = command.indexOf(' ');
    if (space <= 0) {
      return escapeHtmlString(command);
    }

    const kind = getCommandKind(command);
    const sanitized = escapeHtmlString(command.substring(space + 1));

    const handler = kindHandlers[kind || ''];
    if (handler) {
      return handler(sanitized);
    } else {
      return sanitized;
    }
  };

  const command: string = getWithoutStep(entry.message);
  return (
    <>
      <Conditional
        if={fromName(entry.message) || isSecondaryFrom(entry.message)}
      >
        <hr />
        <div style={{paddingBottom: '2em'}} />
      </Conditional>
      <span className="dockerfile-command dockerfile-command-element">
        <Conditional if={!isNullOrUndefined(getCommandKind(command))}>
          <span className={`label ${getCommandKind(command)}`}>
            {getCommandKind(command)}
          </span>
        </Conditional>
        <span className="command-title">{getCommandTitleHtml(command)}</span>
      </span>
    </>
  );
}

function BuildLogError({
  entry,
  entries,
}: {
  entry: BuildLogEntry;
  entries: BuildLogEntry[];
}) {
  const config = useQuayConfig();
  const domain = config?.config.SERVER_HOSTNAME;

  let isPullError = false;
  if (isNullOrUndefined(entry?.data?.base_error)) {
    isPullError =
      entry.data.base_error.indexOf(
        'Error: Status 403 trying to pull repository ',
      ) == 0;
  }

  const localInfo = {
    isLocal: false,
    username: null,
    repo: null,
  };

  // Find the 'pulling' phase entry, and then extra any metadata found under
  // it.
  for (let i = 0; i < entries.length; ++i) {
    const entry = entries[i];
    if (entry.type == 'phase' && entry.message == 'pulling') {
      const entryData = entry.data || {};
      if (entry.data.base_image) {
        localInfo.isLocal = entryData['base_image'].indexOf(domain + '/') == 0;
        localInfo.username = entryData['pull_username'];
        localInfo.repo = entryData['base_image'].substring(domain.length);
      }
      break;
    }
  }

  return (
    <>
      <Conditional if={isPullError && localInfo.isLocal}>
        <Conditional if={!localInfo.username}>
          Error 403: Could not pull private base image{' '}
          <a href={`/repository/${localInfo.repo}`}>{localInfo.repo}</a> without
          robot account credentials.
        </Conditional>
        <Conditional if={localInfo.username}>
          Error 403: Could not pull private base image{' '}
          <a href={`/repository${localInfo.repo}`}>{localInfo.repo}</a> because
          robot account <strong>{localInfo.username}</strong> does not have
          access.
        </Conditional>
        <Conditional if={!isPullError || !localInfo.isLocal}>
          {entry.message}
        </Conditional>
        {/*
    These angular components will need to be implemented during the superuser implementation
    <div bo-if="getBaseError(error) && isSuperuser">
      Base Error Information: <pre>{{ getBaseError(entries) }}</pre>
    </div>
    <div bo-if="getInternalError(entries) && isSuperuser">
      Internal Error Information: <pre>{{ getInternalError(entries) }}</pre>
    </div>
     */}
      </Conditional>
    </>
  );
}
